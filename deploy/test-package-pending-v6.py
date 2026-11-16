"""Negative controls for the V6 packaging verifier; never train models."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("package_v6", Path(__file__).with_name("package-pending-v6.py"))
v6 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v6)
EXPERIMENT = v6.DOWNLOADS / "APF3_Grupo2_Experimento_V6"


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.report = v6.load(EXPERIMENT / "pending_v6_report.json")

    def test_actual_report_equal(self):
        self.assertTrue(v6.all_equal(v6.compare_reports(self.report, self.report)))
        self.assertTrue(v6.validate_artifacts(EXPERIMENT))

    def test_every_actual_raw_and_policy_metric_mutation_detected(self):
        for model in v6.MODELS:
            for split in v6.SPLITS:
                for policy in (False, True):
                    actual = copy.deepcopy(self.report)
                    metrics = (actual["models"][model]["review_policy"][split]["metrics"]
                               if policy else actual["models"][model][split])
                    metrics["recall"] += 0.001
                    with self.subTest(model=model, split=split, policy=policy):
                        self.assertFalse(v6.all_equal(v6.compare_reports(self.report, actual)))

    def test_missing_and_extra_manifest_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for source in EXPERIMENT.iterdir():
                if source.is_file():
                    (folder / source.name).write_bytes(source.read_bytes())
            for filename, key in (("artifact_manifest.json", "tree.joblib"),
                                  ("freeze_before_final.json", "files"),
                                  ("frozen_selection.json", "decision_sha256")):
                original = v6.load(folder / filename)
                altered = copy.deepcopy(original)
                altered.pop(key)
                v6.write(folder / filename, altered)
                with self.subTest(filename=filename), self.assertRaises((ValueError, KeyError)):
                    v6.validate_artifacts(folder)
                v6.write(folder / filename, original)
                # Restore exact bytes, not reserialized hash-chain evidence.
                (folder / filename).write_bytes((EXPERIMENT / filename).read_bytes())
            manifest = v6.load(folder / "artifact_manifest.json")
            manifest["unexpected.joblib"] = "0" * 64
            v6.write(folder / "artifact_manifest.json", manifest)
            with self.assertRaises(ValueError):
                v6.validate_artifacts(folder)

    def test_runtime_drift_rejected(self):
        expected = self.report["provenance"]["runtime"]
        env = {"python": "3.12.14", "prefix": "/repro-env/venv", "base_prefix": "/usr/local",
               "venv_config": "include-system-site-packages = false", "sys_path": [],
               "packages": {("scikit-learn" if n == "sklearn" else n):
                            {"version": ver, "location": "/repro-env/venv/lib/site-packages"}
                            for n, ver in expected.items() if n != "python"}}
        self.assertTrue(v6.validate_environment(env, expected))
        for name in expected:
            actual = copy.deepcopy(env)
            if name == "python":
                actual["python"] = "3.12.13"
            else:
                actual["packages"]["scikit-learn" if name == "sklearn" else name]["version"] = "0.0.0"
            with self.subTest(name=name), self.assertRaises(ValueError):
                v6.validate_environment(actual, expected)

    def test_only_declared_time_and_serialization_exceptions(self):
        actual = copy.deepcopy(self.report)
        actual["provenance"]["recorded_utc"] = "another execution"
        actual["selection"]["decision_sha256"]["provenance.json"] = "new hash"
        self.assertTrue(v6.all_equal(v6.compare_reports(self.report, actual)))
        actual["selection"]["global_winner"]["threshold"] += 0.1
        self.assertFalse(v6.all_equal(v6.compare_reports(self.report, actual)))

    def test_wrapper_and_source_contract(self):
        compile(v6.WRAPPER, "wrapper", "exec")
        self.assertIn("academic_credit_pending_v6.py", v6.WRAPPER)
        self.assertEqual(len(self.report["feature_names"]), 11)
        self.assertEqual(len(v6.DEV_NAMES), 12)
        self.assertEqual(len(v6.PROTO_NAMES), 10)
        self.assertEqual(v6.sha(EXPERIMENT / "protocol.json"), v6.PROTOCOL_SHA)
        self.assertEqual(json.loads((EXPERIMENT / "illustrative_input.json").read_bytes())["features"],
                         self.report["illustrative_inference"]["features"])

    def test_compact_summary_preserves_actual_counts_and_audits(self):
        summary = v6.summary(self.report, EXPERIMENT)
        self.assertEqual(summary["study_counts"]["final.csv"]["unknown"], 4)
        self.assertEqual(summary["study_counts"]["final.csv"]["known"], 276)
        self.assertEqual(len(summary["audit_summary"]), 3)
        self.assertEqual(summary["global_winner"]["family"], "tree")
        self.assertLess(len(json.dumps(summary)), 40000)


if __name__ == "__main__":
    unittest.main()
