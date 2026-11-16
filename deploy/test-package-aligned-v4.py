"""Standard-library tests for packaging guards, exact comparisons and CSV scope."""

import contextlib
import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "package_aligned_v4", Path(__file__).with_name("package-aligned-v4.py")
)
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


def chain_fixture(folder):
    folder.mkdir()
    for name in PACKAGE.DECISION_FILES:
        PACKAGE.write_json(folder / name, {})
    provenance = {"feature_names": ["x"], "runtime": {"python": "3.12.14", "numpy": "2.5.3"}}
    PACKAGE.write_json(folder / "provenance.json", provenance)
    families = {
        name: {
            "family": name,
            "candidate_index": index,
            "params": {"family": name},
            "threshold": 0.1,
            "metrics": {},
            "review_policy": {},
        }
        for index, name in enumerate(("tree", "svm"))
    }
    selection = {
        "version": "academic-owner-aligned-v4",
        "frozen_utc": "old",
        "feature_names": ["x"],
        "families": families,
        "global_winner": families["svm"],
        "baselines": {
            name: {"params": {"family": name}, "threshold": 0.5, "metrics": {}, "review_policy": {}}
            for name in ("most_frequent", "constant_1")
        },
        "decision_sha256": {name: PACKAGE.sha(folder / name) for name in PACKAGE.DECISION_FILES},
        "source_anchors_dict_sha256": "anchors",
        "research_only": True,
        "oof_caveat": "synthetic",
        "selection_metric": "F2",
    }
    PACKAGE.write_json(folder / "frozen_selection.json", selection)
    for name in PACKAGE.ARTIFACT_FILES - {"frozen_selection.json"}:
        PACKAGE.write_json(folder / name, "svm" if name == "selected_model.joblib" else name[:-7])
    manifest = {name: PACKAGE.sha(folder / name) for name in PACKAGE.ARTIFACT_FILES}
    PACKAGE.write_json(folder / "artifact_manifest.json", manifest)
    PACKAGE.write_json(
        folder / "aligned_v4_report.json",
        {
            "selection": selection,
            "provenance": provenance,
            "artifact_sha256": manifest,
            "models": dict.fromkeys(PACKAGE.MODELS, {}),
        },
    )


def copy_package(source, root):
    for folder in ("codigo", "datos", "experimento", "reproduccion"):
        shutil.copytree(source / folder, root / folder)
    for name in (
        "manifest-paquete.json",
        "requirements.txt",
        "reproducir-v4.py",
        "entorno-empaquetado.json",
        "entorno-reproduccion.json",
        "inferencia-original.json",
        "inferencia-reproduccion.json",
        "comandos-reproduccion.json",
    ):
        shutil.copyfile(source / name, root / name)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "generated_utc": "old",
            "provenance": {"recorded_utc": "old", "code": "same"},
            "selection": {
                "frozen_utc": "old",
                "decision_sha256": {"provenance.json": "old-hash", "protocol.json": "same-hash"},
                "global_winner": {"family": "tree", "threshold": 0.2},
            },
            "artifact_sha256": {name: "old-hash" for name in PACKAGE.ARTIFACT_FILES},
            "models": {
                name: {
                    **{
                        split: {"recall": 0.5, "confusion_matrix": [[4, 1], [2, 3]]}
                        for split in PACKAGE.SPLITS
                    },
                    "review_policy": {
                        split: {"reviews_unknown": 1, "daily": [{"reviews": 2}]}
                        for split in PACKAGE.SPLITS
                    },
                }
                for name in PACKAGE.MODELS
            },
            "illustrative_inference": {"probability": 0.25},
        }

    def test_exact_equality_and_nonmutation(self):
        previous = copy.deepcopy(self.report)
        self.assertTrue(PACKAGE.all_equal(PACKAGE.compare_reports(self.report, self.report)))
        self.assertEqual(self.report, previous)

    def test_only_explicit_timestamps_and_derived_hashes_excluded(self):
        actual = copy.deepcopy(self.report)
        actual["generated_utc"] = "new"
        actual["provenance"]["recorded_utc"] = "new"
        actual["selection"]["frozen_utc"] = "new"
        actual["selection"]["decision_sha256"]["provenance.json"] = "new-hash"
        actual["artifact_sha256"]["frozen_selection.json"] = "new-hash"
        self.assertTrue(PACKAGE.all_equal(PACKAGE.compare_reports(self.report, actual)))

    def test_every_raw_and_policy_comparison_rejects_mismatch(self):
        for model in PACKAGE.MODELS:
            for split in PACKAGE.SPLITS:
                with self.subTest(model=model, split=split):
                    actual = copy.deepcopy(self.report)
                    actual["models"][model][split]["recall"] += 1e-15
                    self.assertFalse(
                        PACKAGE.all_equal(PACKAGE.compare_reports(self.report, actual))
                    )
                    actual = copy.deepcopy(self.report)
                    actual["models"][model]["review_policy"][split]["reviews_unknown"] += 1
                    self.assertFalse(
                        PACKAGE.all_equal(PACKAGE.compare_reports(self.report, actual))
                    )

    def test_selection_mismatch_rejected(self):
        actual = copy.deepcopy(self.report)
        actual["selection"]["global_winner"] = "changed"
        self.assertFalse(PACKAGE.all_equal(PACKAGE.compare_reports(self.report, actual)))
        actual = copy.deepcopy(self.report)
        actual["selection"]["decision_sha256"]["protocol.json"] = "changed"
        self.assertFalse(PACKAGE.all_equal(PACKAGE.compare_reports(self.report, actual)))

    def test_normalization_requires_exact_artifact_keys(self):
        for mutation in ("missing", "extra"):
            actual = copy.deepcopy(self.report)
            if mutation == "missing":
                actual["artifact_sha256"].pop("svm.joblib")
            else:
                actual["artifact_sha256"]["extra.joblib"] = "hash"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                PACKAGE.normalized_report(actual)

    def test_manifest_and_report_missing_extra_or_bad_hash_fail_before_loading(self):
        for folder in ("experimento", "reproduccion"):
            for target in ("manifest", "report", "both"):
                for mutation in ("missing", "extra", "hash"):
                    with self.subTest(folder=folder, target=target, mutation=mutation):
                        with tempfile.TemporaryDirectory() as temporary:
                            root = Path(temporary)
                            for name in ("experimento", "reproduccion"):
                                chain_fixture(root / name)
                            path = root / folder
                            manifest = PACKAGE.load(path / "artifact_manifest.json")
                            report = PACKAGE.load(path / "aligned_v4_report.json")
                            maps = []
                            if target in ("manifest", "both"):
                                maps.append(manifest)
                            if target in ("report", "both"):
                                maps.append(report["artifact_sha256"])
                            for mapping in maps:
                                if mutation == "missing":
                                    mapping.pop("svm.joblib")
                                elif mutation == "extra":
                                    mapping["./svm.joblib"] = manifest["svm.joblib"]
                                else:
                                    mapping["svm.joblib"] = "0" * 64
                            PACKAGE.write_json(path / "artifact_manifest.json", manifest)
                            PACKAGE.write_json(path / "aligned_v4_report.json", report)
                            with patch.object(PACKAGE.subprocess, "run") as run:
                                with self.assertRaises(ValueError):
                                    PACKAGE.inspect_artifacts(root, Path("/runtime"), "image")
                                run.assert_not_called()

    def test_selection_and_decision_schema_and_hashes_are_required(self):
        for section in ("selection", "decision", "families", "baselines", "winner"):
            for mutation in ("missing", "extra", "hash"):
                if mutation == "hash" and section != "decision":
                    continue
                with self.subTest(section=section, mutation=mutation):
                    with tempfile.TemporaryDirectory() as temporary:
                        folder = Path(temporary) / "evidence"
                        chain_fixture(folder)
                        selection = PACKAGE.load(folder / "frozen_selection.json")
                        mapping = (
                            selection
                            if section == "selection"
                            else selection[
                                {
                                    "decision": "decision_sha256",
                                    "families": "families",
                                    "baselines": "baselines",
                                    "winner": "global_winner",
                                }[section]
                            ]
                        )
                        if mutation == "missing":
                            mapping.pop(next(iter(mapping)))
                        elif mutation == "extra":
                            mapping["extra"] = "hash"
                        else:
                            mapping["protocol.json"] = "0" * 64
                        PACKAGE.write_json(folder / "frozen_selection.json", selection)
                        manifest = PACKAGE.load(folder / "artifact_manifest.json")
                        manifest["frozen_selection.json"] = PACKAGE.sha(
                            folder / "frozen_selection.json"
                        )
                        report = PACKAGE.load(folder / "aligned_v4_report.json")
                        report["selection"], report["artifact_sha256"] = selection, manifest
                        PACKAGE.write_json(folder / "artifact_manifest.json", manifest)
                        PACKAGE.write_json(folder / "aligned_v4_report.json", report)
                        with self.assertRaises(ValueError):
                            PACKAGE.validate_artifact_chains(folder)

    def test_selected_model_must_be_byte_identical_to_svm(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "evidence"
            chain_fixture(folder)
            self.assertTrue(PACKAGE.validate_artifact_chains(folder))
            PACKAGE.write_json(folder / "selected_model.joblib", "different model")
            manifest = PACKAGE.load(folder / "artifact_manifest.json")
            manifest["selected_model.joblib"] = PACKAGE.sha(folder / "selected_model.joblib")
            report = PACKAGE.load(folder / "aligned_v4_report.json")
            report["artifact_sha256"] = manifest
            PACKAGE.write_json(folder / "artifact_manifest.json", manifest)
            PACKAGE.write_json(folder / "aligned_v4_report.json", report)
            with self.assertRaisesRegex(ValueError, "Selected model SHA256"):
                PACKAGE.validate_artifact_chains(folder)

    def test_probe_persists_current_runtime_even_when_unclean_or_wrong_version(self):
        for drift in ("python", "numpy", "inherited", "foreign_path"):
            environment = {
                "python": "3.12.14",
                "prefix": "/repro-env/venv",
                "base_prefix": "/usr/local",
                "venv_config": "include-system-site-packages = false\n",
                "sys_path": ["/repro-env/venv/lib/python3.12/site-packages"],
                "packages": {"numpy": {"version": "2.5.3", "location": "/repro-env/venv/lib/"}},
            }
            if drift == "python":
                environment["python"] = "3.12.13"
            elif drift == "numpy":
                environment["packages"]["numpy"]["version"] = "different"
            elif drift == "inherited":
                environment["venv_config"] = "include-system-site-packages = true\n"
            else:
                environment["sys_path"].append("/usr/local/lib/python3.12/site-packages")
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as temporary:
                record = Path(temporary) / "entorno-verificacion.json"
                with patch.object(
                    PACKAGE.subprocess,
                    "run",
                    side_effect=[
                        Mock(stdout=json.dumps(environment)),
                        Mock(stdout='[{"Id":"sha256:current-image"}]'),
                    ],
                ):
                    with self.assertRaises(ValueError):
                        PACKAGE.probe_environment(
                            Path("/current-venv"),
                            "current-image",
                            {"python": "3.12.14", "numpy": "2.5.3"},
                            record_path=record,
                        )
                observed = PACKAGE.load(record)
                self.assertEqual(observed["python"], environment["python"])
                self.assertEqual(observed["image"], "sha256:current-image")
                self.assertEqual(observed["clean_venv"], drift not in ("inherited", "foreign_path"))

    def test_current_image_or_venv_drift_blocks_artifact_loading(self):
        for drift in ("image", "packages", "venv_config"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for folder in ("experimento", "reproduccion"):
                    chain_fixture(root / folder)
                recorded = {"image": "sha256:recorded", "packages": {}, "venv_config": "clean"}
                for filename in ("entorno-empaquetado.json", "entorno-reproduccion.json"):
                    PACKAGE.write_json(root / filename, recorded)
                current = {**recorded, drift: "different"}
                with patch.object(PACKAGE, "probe_environment", return_value=current) as probe:
                    with patch.object(PACKAGE.subprocess, "run") as run:
                        with self.assertRaisesRegex(ValueError, "environment drift"):
                            PACKAGE.inspect_artifacts(root, Path("/current-venv"), "current-image")
                        probe.assert_called_once_with(
                            Path("/current-venv"),
                            "current-image",
                            {"python": "3.12.14", "numpy": "2.5.3"},
                            record_path=root / "entorno-verificacion.json",
                        )
                        run.assert_not_called()

    def test_study_export_keeps_unknowns_and_excludes_warmup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [
                {"phase": "warmup", "late_payment": 0},
                {"phase": "study", "late_payment": 1},
                {"phase": "study", "late_payment": None},
            ]
            PACKAGE.write_json(
                root / "development_transactions.json", {"replicas": [{"rows": rows}]}
            )
            PACKAGE.write_json(root / "final_transactions.json", {"rows": rows})
            for exported in PACKAGE.study_rows(root).values():
                self.assertEqual(exported, rows[1:])

    def test_cli_fails_closed_and_persists_missing_evidence(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(PACKAGE.main(["--root", temporary, "--action", "verify"]), 1)
            self.assertFalse(
                PACKAGE.load(Path(temporary) / "verificacion-reproduccion.json")["passed"]
            )

    def test_docker_is_offline_and_sources_readonly(self):
        command = PACKAGE.docker_base(Path("/package-host"), Path("/venv-host"), PACKAGE.IMAGE)
        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertIn("--read-only", command)
        for destination in ("codigo", "experimento", "datos"):
            self.assertTrue(any(f"dst=/package/{destination},readonly" in item for item in command))
        self.assertIn("type=bind,src=/venv-host,dst=/repro-env,readonly", command)
        self.assertEqual(command[-2:], ["-I", "-B"])

    @unittest.skipUnless(os.environ.get("ALIGNED_V4_PACKAGE_ROOT"), "Requires completed package")
    def test_completed_package_cli_rejects_changed_metric_in_disposable_copy(self):
        source = Path(os.environ["ALIGNED_V4_PACKAGE_ROOT"])
        before = PACKAGE.inventory(source / "experimento")
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stderr(io.StringIO()):
            root = Path(temporary)
            copy_package(source, root)
            path = root / "reproduccion/aligned_v4_report.json"
            actual = PACKAGE.load(path)
            actual["models"]["tree"]["final"]["recall"] += 0.001
            PACKAGE.write_json(path, actual)
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(root / "reproducir-v4.py"),
                    "--root",
                    str(root),
                    "--action",
                    "verify",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
            failure = PACKAGE.load(root / "verificacion-reproduccion.json")
            self.assertFalse(failure["passed"])
            self.assertFalse(failure["checks"]["raw"]["tree/final"])
            self.assertTrue(failure["checks"]["integrity"]["frozen_experiment_unchanged"])
        self.assertEqual(PACKAGE.inventory(source / "experimento"), before)
        PACKAGE.archive_existing(source / "prueba-negativa-verificador.json")
        PACKAGE.write_json(
            source / "prueba-negativa-verificador.json",
            {
                "passed": True,
                "exit_code": process.returncode,
                "method": (
                    "Real CLI subprocess on disposable package copy; original evidence unchanged"
                ),
                "mutation": "reproduccion/aligned_v4_report.json models.tree.final.recall += 0.001",
                "metric_mismatch_detected": not failure["checks"]["raw"]["tree/final"],
                "source_experiment_unchanged": PACKAGE.inventory(source / "experimento") == before,
            },
        )

    @unittest.skipUnless(os.environ.get("ALIGNED_V4_PACKAGE_ROOT"), "Requires completed package")
    def test_completed_package_cli_rejects_manifest_holes_without_deserialization(self):
        source = Path(os.environ["ALIGNED_V4_PACKAGE_ROOT"])
        before = PACKAGE.inventory(source / "experimento")
        results = {}
        for mutation in ("missing", "extra", "hash"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                copy_package(source, root)
                folder = root / "reproduccion"
                manifest = PACKAGE.load(folder / "artifact_manifest.json")
                report = PACKAGE.load(folder / "aligned_v4_report.json")
                if mutation == "missing":
                    manifest.pop("svm.joblib")
                elif mutation == "extra":
                    manifest["./svm.joblib"] = manifest["svm.joblib"]
                else:
                    manifest["svm.joblib"] = "0" * 64
                report["artifact_sha256"] = manifest
                PACKAGE.write_json(folder / "artifact_manifest.json", manifest)
                PACKAGE.write_json(folder / "aligned_v4_report.json", report)
                process = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(root / "reproducir-v4.py"),
                        "--root",
                        str(root),
                        "--action",
                        "verify",
                    ],
                    text=True,
                    capture_output=True,
                )
                failure = PACKAGE.load(root / "verificacion-reproduccion.json")
                self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
                self.assertFalse(failure["passed"])
                self.assertFalse((root / "estado-artefactos.json").exists())
                self.assertFalse((root / "entorno-verificacion.json").exists())
                results[mutation] = {
                    "exit_code": process.returncode,
                    "error": failure["error"],
                    "failed_before_runtime_or_artifact_loading": True,
                }
        self.assertEqual(PACKAGE.inventory(source / "experimento"), before)
        record = source / "prueba-negativa-manifiestos.json"
        PACKAGE.archive_existing(record)
        PACKAGE.write_json(
            record, {"passed": True, "results": results, "source_experiment_unchanged": True}
        )

    @unittest.skipUnless(os.environ.get("ALIGNED_V4_PACKAGE_ROOT"), "Requires completed package")
    def test_learned_state_detects_array_attribute_missing_key_and_native_tree_changes(self):
        root = Path(os.environ["ALIGNED_V4_PACKAGE_ROOT"])
        command = PACKAGE.docker_base(root, PACKAGE.VENV_PARENT.resolve(), PACKAGE.IMAGE) + [
            "-c",
            PACKAGE.STATE_PROBE
            + """
import copy
model = joblib.load('/package/experimento/tree.joblib')
expected = state(model)
for mutation in ('array', 'attribute', 'missing_key', 'native_tree'):
    changed = copy.deepcopy(model)
    classifier = changed.named_steps['classifier']
    if mutation == 'array':
        changed.named_steps['imputer'].statistics_[0] += 0.125
    elif mutation == 'attribute':
        classifier.max_depth += 1
    elif mutation == 'missing_key':
        del classifier.n_features_in_
    else:
        native = classifier.tree_.__getstate__()
        native['nodes']['threshold'][0] += 0.125
        classifier.tree_.__setstate__(native)
    assert state(changed) != expected, mutation
assert state(model) == expected
print('Four learned-state negative controls detected; model unchanged')
""",
        ]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
