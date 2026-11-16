"""Self-contained stdlib tests; fake opaque model bytes, no ML dependencies."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "prepare_v4", Path(__file__).with_name("prepare-aligned-v4-lab.py")
)
preparer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preparer)


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / "package"
        self.experiment = self.source / "experimento"
        self.experiment.mkdir(parents=True)
        self.destination = self.root / "academic" / "v4"
        for name in preparer.EXPERIMENT_FILES:
            (self.experiment / name).write_bytes(b"opaque, not a pickle")
        self.write(
            "protocol.json",
            {
                "version": preparer.VERSION,
                "illustrative_input": preparer.ILLUSTRATIVE,
            },
        )
        self.write("illustrative_input.json", {"features": preparer.ILLUSTRATIVE})
        self.provenance = {
            "runtime": dict(preparer.RUNTIME),
            "feature_names": list(preparer.ILLUSTRATIVE),
            "source_anchors": {"client_cap_pen": 80},
            "protocol_sha256": self.digest("protocol.json"),
            "calibration_sha256": self.digest("calibration.json"),
        }
        self.frozen = {
            "version": preparer.VERSION,
            "research_only": True,
            "feature_names": list(preparer.ILLUSTRATIVE),
            "global_winner": {"family": "svm", "params": {"family": "svm"}, "threshold": 0.1},
        }
        self.seal()

    def write(self, name, value):
        (self.experiment / name).write_text(json.dumps(value), encoding="ascii")

    def digest(self, name):
        return preparer.sha((self.experiment / name).read_bytes())

    def seal(self):
        self.write("provenance.json", self.provenance)
        self.frozen["decision_sha256"] = {
            name: self.digest(name)
            for name in ("protocol.json", "calibration.json", "provenance.json")
        }
        self.write("frozen_selection.json", self.frozen)
        artifacts = {
            name: self.digest(name) for name in ("selected_model.joblib", "frozen_selection.json")
        }
        self.write("artifact_manifest.json", artifacts)
        self.report = {
            "version": preparer.VERSION,
            "origen": "simulado",
            "research_only": True,
            "business_approval": False,
            "feature_names": list(preparer.ILLUSTRATIVE),
            "selection": self.frozen,
            "provenance": self.provenance,
            "artifact_sha256": artifacts,
            "models": {"svm": {"threshold": 0.1}},
        }
        self.write("aligned_v4_report.json", self.report)
        self.rehash()

    def rehash(self):
        self.manifest = {
            "version": "aligned-v4-self-contained-1",
            "experiment_sha256": {name: self.digest(name) for name in preparer.EXPERIMENT_FILES},
        }
        self.save_manifest()

    def save_manifest(self):
        (self.source / "manifest-paquete.json").write_text(json.dumps(self.manifest))

    def rejected(self):
        with self.assertRaises((ValueError, OSError, KeyError, TypeError)):
            preparer.prepare(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.destination.parent.exists())

    def test_cli_exact_bundle_and_checks(self):
        before = {name: self.digest(name) for name in preparer.EXPERIMENT_FILES}
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                str(Path(preparer.__file__)),
                "--source",
                str(self.source),
                "--destination",
                str(self.destination),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        checks = json.loads(result.stdout)
        self.assertEqual(checks["experiment_hashes_checked"], 24)
        self.assertFalse(checks["checks"]["model_loaded"])
        self.assertFalse(checks["checks"]["inference_executed"])
        self.assertEqual(
            {p.name for p in self.destination.iterdir()},
            set(preparer.FILES) | {"web_manifest.json"},
        )
        web = json.loads((self.destination / "web_manifest.json").read_bytes())
        self.assertEqual(
            web,
            {"version": preparer.VERSION, "files": {name: before[name] for name in preparer.FILES}},
        )
        for name in preparer.FILES:
            self.assertEqual(
                (self.destination / name).read_bytes(), (self.experiment / name).read_bytes()
            )
        self.assertEqual(before, {name: self.digest(name) for name in preparer.EXPERIMENT_FILES})

    def test_corrupt_web_or_nonweb_file(self):
        for name in ("selected_model.joblib", "final_predictions.csv"):
            with self.subTest(name=name):
                path = self.experiment / name
                original = path.read_bytes()
                path.write_bytes(b"corrupted")
                self.rejected()
                path.write_bytes(original)

    def test_missing_required_input(self):
        (self.experiment / "illustrative_input.json").unlink()
        self.rejected()

    def test_wrong_manifest_set_or_unsafe_name(self):
        for name in ("../outside", "/outside", "unknown.json"):
            with self.subTest(name=name):
                manifest = copy.deepcopy(self.manifest)
                manifest["experiment_sha256"][name] = manifest["experiment_sha256"].pop(
                    "selected_model.joblib"
                )
                (self.source / "manifest-paquete.json").write_text(json.dumps(manifest))
                self.rejected()

    def test_no_overwrite_even_empty_directory(self):
        self.destination.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "new directory"):
            preparer.prepare(self.source, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_existing_file_untouched(self):
        self.destination.parent.mkdir()
        self.destination.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            preparer.prepare(self.source, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"keep")

    def test_source_symlink_file_and_directory(self):
        for path in (
            self.experiment / "selected_model.joblib",
            self.experiment,
            self.source / "manifest-paquete.json",
        ):
            with self.subTest(path=path):
                moved = path.with_name(path.name + ".original")
                path.rename(moved)
                path.symlink_to(moved, target_is_directory=moved.is_dir())
                self.rejected()
                path.unlink()
                moved.rename(path)

    def test_destination_symlink_and_parent(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.destination.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            preparer.prepare(self.source, self.destination)
        self.assertEqual(list(outside.iterdir()), [])
        self.destination.parent.unlink()
        self.destination.parent.mkdir()
        self.destination.symlink_to(outside / "missing")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            preparer.prepare(self.source, self.destination)
        self.assertFalse((outside / "missing").exists())

    def test_destination_inside_source(self):
        with self.assertRaisesRegex(ValueError, "inside the package"):
            preparer.prepare(self.source, self.source / "web")
        self.assertFalse((self.source / "web").exists())

    def test_wrong_runtime_family_or_research(self):
        mutations = (
            ("runtime", lambda: self.provenance["runtime"].update(python="3.12.0")),
            ("family", lambda: self.frozen["global_winner"].update(family="tree")),
            ("research", lambda: self.frozen.update(research_only=False)),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                old_provenance, old_frozen = copy.deepcopy((self.provenance, self.frozen))
                mutate()
                self.seal()
                self.rejected()
                self.provenance, self.frozen = old_provenance, old_frozen

    def test_report_mismatch_and_business_approval(self):
        for field, value in (
            ("selection", {}),
            ("provenance", {}),
            ("business_approval", True),
            ("research_only", 1),
        ):
            with self.subTest(field=field):
                changed = {**self.report, field: value}
                self.write("aligned_v4_report.json", changed)
                self.rehash()
                self.rejected()

    def test_frozen_hash_mismatch(self):
        self.frozen["decision_sha256"]["protocol.json"] = "0" * 64
        self.write("frozen_selection.json", self.frozen)
        self.report["selection"] = self.frozen
        self.write("aligned_v4_report.json", self.report)
        self.rehash()
        self.rejected()

    def test_exact_illustrative_input_and_cap(self):
        for features in (
            {**preparer.ILLUSTRATIVE, "requested_ratio": 0.5},
            {**preparer.ILLUSTRATIVE, "pending_overdue": False},
            {**preparer.ILLUSTRATIVE, "label": 0},
        ):
            with self.subTest(features=features):
                self.write("illustrative_input.json", {"features": features})
                self.rehash()
                self.rejected()
        self.write("illustrative_input.json", {"features": preparer.ILLUSTRATIVE})
        self.provenance["source_anchors"]["client_cap_pen"] = 100
        self.seal()
        self.rejected()

    def test_duplicate_and_nonfinite_json(self):
        for raw in (b'{"version": "x", "version": "y"}', b'{"value": NaN}'):
            (self.source / "manifest-paquete.json").write_bytes(raw)
            self.rejected()


if __name__ == "__main__":
    unittest.main()
