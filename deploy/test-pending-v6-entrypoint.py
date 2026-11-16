"""Stdlib-only subprocess checks for the delivery's pre-model boundary."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "deploy/templates/pending-v6-entrypoint.py"
POLICY = REPO / "backend/app/services/academic_v6_policy.py"
DELIVERY = Path.home() / "Downloads/APF3_Grupo2_Entrega_V6"
FEATURES = {
    "completed_sales": 4, "paid_credits": 4, "paid_late": 1,
    "pending_overdue": 0, "pending_current": 0, "outstanding": 0,
    "utilization": 0, "requested_ratio": 0.25, "tenure_days": 120,
    "punctuality_rate": 0.75, "overdue_rate": 0,
}
PENDING = ("pending_overdue", "pending_current", "outstanding", "utilization", "overdue_rate")
SENTINEL = '''import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[2]
(root / "runner-called").write_text(json.dumps(sys.argv[1:]))
for index, arg in enumerate(sys.argv[1:], 1):
    if arg == "--output-json" or arg.startswith("--output-json="):
        output = arg.split("=", 1)[1] if "=" in arg else sys.argv[index + 1]
        with Path(output).open("x") as stream:
            stream.write('{"sentinel": "unchanged runner output"}\\n')
print("sentinel delegated")
'''


class EntrypointTests(unittest.TestCase):
    python_flags = ("-B",)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wrapper = self.root / "entrypoint.py"
        shutil.copyfile(TEMPLATE, self.wrapper)
        shutil.copyfile(POLICY, self.root / "v6_policy.py")
        scripts = self.root / "codigo/scripts"
        scripts.mkdir(parents=True)
        (scripts / "academic_credit_pending_v6.py").write_text(SENTINEL)
        (self.root / "backend").mkdir()
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.source = self.root / "input.json"
        self.output = self.root / "output.json"
        self.marker = self.root / "runner-called"

    def invoke(self, argv):
        return subprocess.run([sys.executable, *self.python_flags, str(self.wrapper), *map(str, argv)],
                              capture_output=True, text=True, timeout=20)

    def predict(self, changes=None, equals=False, data=None, extra=(), output=None):
        features = {**FEATURES, **(changes or {})}
        self.source.write_text(json.dumps({"features": features} if data is None else data))
        pairs = (("--predict-artifact-dir", self.artifacts), ("--input-json", self.source),
                 ("--output-json", output or self.output))
        argv = ([f"{flag}={value}" for flag, value in pairs] if equals else
                [str(item) for pair in pairs for item in pair])
        return self.invoke([*argv, *extra])

    def assert_gated(self, changes, decision, equals=False):
        self.output.unlink(missing_ok=True)
        result = self.predict(changes, equals=equals)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists(), "Frozen runner was loaded")
        payload = json.loads(self.output.read_text())
        self.assertEqual(payload, json.loads(result.stdout))
        self.assertEqual(payload["decision"], decision)
        self.assertEqual(payload["requires_manual_review"], decision == "requires_owner_review")
        self.assertEqual(payload["version"], "academic-owner-pending-v6")
        self.assertEqual(payload["origen"], "simulado")
        self.assertIs(payload["research_only"], True)
        self.assertIs(payload["business_approval"], False)
        self.assertIs(payload["model_called"], False)
        for name in ("probability", "predicted", "threshold"):
            self.assertIsNone(payload[name])
        self.assertEqual(payload["features"], {**FEATURES, **changes})
        self.assertTrue(payload["reason"])
        self.assertTrue(payload["reason"].isascii())

    def test_all_debt_signals_block_without_loading_runner(self):
        for name in PENDING:
            for equals in (False, True):
                with self.subTest(name=name, equals=equals):
                    value = 1 if name.startswith("pending_") else 0.001
                    self.assert_gated({name: value}, "blocked_pending_balance", equals)

    def test_partial_balance_blocks_even_without_pending_counts(self):
        self.assert_gated({"outstanding": 0.01}, "blocked_pending_balance")

    def test_missing_pending_fields_require_review(self):
        for name in PENDING:
            with self.subTest(name=name):
                self.assert_gated({name: None}, "requires_owner_review")

    def test_no_fully_repaid_credit_requires_review(self):
        self.assert_gated({"completed_sales": 0, "paid_credits": 0, "paid_late": 0,
                           "punctuality_rate": 0}, "requires_owner_review", equals=True)

    def test_unknown_paid_history_requires_review(self):
        self.assert_gated({"paid_credits": None}, "requires_owner_review")
        self.assert_gated({"completed_sales": None, "paid_credits": None,
                           "paid_late": None, "punctuality_rate": None},
                          "requires_owner_review", equals=True)

    def test_debt_precedes_missing_pending_or_paid_history(self):
        for paid in (None, 0):
            with self.subTest(paid=paid):
                self.assert_gated({"completed_sales": paid, "paid_credits": paid,
                                   "paid_late": 0, "punctuality_rate": 0,
                                   "pending_current": None, "outstanding": 0.01},
                                  "blocked_pending_balance")

    def test_malformed_features_rejected_before_guard(self):
        cases = [
            {"outstanding": "1"}, {"outstanding": True}, {"outstanding": -1},
            {"outstanding": float("nan")}, {"outstanding": float("inf")},
            {"outstanding": 10 ** 400}, {"pending_current": 0.5},
            {"paid_credits": False}, {"completed_sales": 1.2}, {"tenure_days": 0.2},
            {"utilization": 1.1}, {"overdue_rate": 1.1}, {"punctuality_rate": 1.1},
            {"requested_ratio": None}, {"requested_ratio": 0}, {"requested_ratio": 0.7},
            {"paid_late": 5}, {"completed_sales": 3}, {"punctuality_rate": 0.5},
            {"paid_credits": 0, "completed_sales": 0},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                result = self.predict({"pending_current": 1, **changes}, equals=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(self.output.exists())
                self.assertFalse(self.marker.exists())

    def test_invalid_json_shapes_and_syntax(self):
        for data in ([], {"features": FEATURES, "label": 0}, {"features": []},
                     {**FEATURES, "label": 0}, {"paid_credits": 0}):
            with self.subTest(data=data):
                result = self.predict(data=data)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(self.marker.exists())
        self.source.write_text("{")
        result = self.invoke(["--predict-artifact-dir", self.artifacts, "--input-json",
                              self.source, "--output-json", self.output])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.marker.exists())

    def test_duplicate_json_keys_rejected_before_guard_or_runner(self):
        features = json.dumps(FEATURES)
        duplicate = '{"outstanding": 1, ' + features[1:]
        escaped = '{"outstand\\u0069ng": 1, ' + features[1:]
        cases = (duplicate, escaped, '{"features": ' + duplicate + '}',
                 '{"features": {}, "features": ' + features + '}')
        for raw in cases:
            with self.subTest(raw=raw):
                self.source.write_text(raw)
                result = self.invoke([f"--predict-artifact-dir={self.artifacts}",
                                      f"--input-json={self.source}",
                                      f"--output-json={self.output}"])
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("Duplicate JSON key:", result.stderr)
                self.assertFalse(self.output.exists())
                self.assertFalse(self.marker.exists())

    def test_output_collision_never_overwrites(self):
        for changes in ({}, {"outstanding": 1}):
            with self.subTest(changes=changes):
                self.output.write_bytes(b"original evidence")
                result = self.predict(changes)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self.output.read_bytes(), b"original evidence")
                self.assertFalse(self.marker.exists())

    def test_protected_output_paths(self):
        for output in (self.root / "codigo/result.json", self.root / "backend/result.json",
                       self.artifacts / "result.json", self.source,
                       self.root / "missing/result.json"):
            with self.subTest(output=output):
                result = self.predict({"outstanding": 1}, output=output)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(self.marker.exists())
        alias = self.root / "artifact-alias"
        alias.symlink_to(self.artifacts, target_is_directory=True)
        result = self.predict({"outstanding": 1}, output=alias / "result.json")
        self.assertEqual(result.returncode, 2)
        dangling = self.root / "dangling.json"
        dangling.symlink_to(self.root / "absent.json")
        result = self.predict({"outstanding": 1}, output=dangling)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / "absent.json").exists())

    def test_strict_flags_and_mode_exclusion(self):
        self.source.write_text(json.dumps(FEATURES))
        cases = [[], ["--input-json", self.source], ["--predict-artifact-dir", self.artifacts],
                 ["--predict-artifact-dir=" + str(self.artifacts), "--input-json=" + str(self.source)],
                 ["--development-dir", "dev", "--protocol-dir", "proto"],
                 ["--predict-artifact", self.artifacts, "--input-json", self.source,
                  "--output-json", self.output]]
        for argv in cases:
            with self.subTest(argv=argv):
                self.assertEqual(self.invoke(argv).returncode, 2)
                self.assertFalse(self.marker.exists())
        for extra in (("--development-dir=dev",), ("--protocol-dir=proto",),
                      ("--output-dir=experiment",), ("--unknown=value",)):
            with self.subTest(extra=extra):
                result = self.predict({"outstanding": 1}, equals=True, extra=extra)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.marker.exists())

    def test_help_does_not_load_runner(self):
        result = self.invoke(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("--predict-artifact-dir", result.stdout)
        self.assertIn("--development-dir", result.stdout)
        self.assertFalse(self.marker.exists())

    def test_eligible_delegates_original_arguments_and_output(self):
        for equals in (False, True):
            with self.subTest(equals=equals):
                self.output.unlink(missing_ok=True)
                result = self.predict(equals=equals)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "sentinel delegated\n")
                self.assertEqual(self.output.read_bytes(), b'{"sentinel": "unchanged runner output"}\n')
                args = json.loads(self.marker.read_text())
                self.assertIn(("--input-json=" + str(self.source)) if equals else
                              str(self.source), args)

    def test_experiment_delegates_only_with_complete_explicit_flags(self):
        argv = ["--development-dir=dev", "--protocol-dir=proto", "--output-dir=experiment"]
        result = self.invoke(argv)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.marker.read_text()), argv)

    def test_shared_helper_and_delivery_are_identical(self):
        spec = importlib.util.spec_from_file_location("policy", POLICY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIsNone(module.pre_model_decision(FEATURES))
        if DELIVERY.is_dir():
            self.assertEqual(POLICY.read_bytes(), (DELIVERY / "v6_policy.py").read_bytes())
            self.assertEqual(TEMPLATE.read_bytes(),
                             (DELIVERY / "APF3_TD_Grupo2_ML_Innovacion.py").read_bytes())


class IsolatedEntrypointTests(EntrypointTests):
    python_flags = ("-I", "-B")


if __name__ == "__main__":
    unittest.main()
