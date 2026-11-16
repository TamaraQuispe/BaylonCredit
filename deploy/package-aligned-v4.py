"""Package frozen V4 sources and verify a clean, offline Docker reproduction."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

CODE_PATHS = {
    "runner": "scripts/academic_credit_aligned_v4.py",
    "pure_helpers": "scripts/academic_credit_grouped_cv.py",
    "generator": "app/ml/owner_aligned_synthetic.py",
    "validator": "app/ml/owner_aligned_synthetic.py",
    **{name: f"app/ml/{name}.py" for name in ("features", "outcomes", "synthetic")},
}
IMAGE = "bayloncredit-api-training-test:latest"
VENV_PARENT = Path("/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/cv3-repro")
MODELS = ("tree", "svm", "most_frequent", "constant_1")
SPLITS = ("train", "oof", "final")
ARTIFACT_FILES = frozenset(
    [*(f"{name}.joblib" for name in (*MODELS, "selected_model")), "frozen_selection.json"]
)
DECISION_FILES = frozenset(
    [
        "protocol.json",
        "calibration.json",
        "provenance.json",
        "development_transactions.json",
        "development_rows.json",
        "development_audits.json",
        "fold_audit.json",
        "cv_search.json",
    ]
)
SELECTION_KEYS = frozenset(
    [
        "version",
        "frozen_utc",
        "feature_names",
        "families",
        "global_winner",
        "baselines",
        "decision_sha256",
        "source_anchors_dict_sha256",
        "research_only",
        "oof_caveat",
        "selection_metric",
    ]
)
README_MARKER = "<!-- aligned-v4-package -->"
PROBE = """
import importlib.metadata as m, json, platform, sys
from pathlib import Path
print(json.dumps({
    'python': platform.python_version(), 'prefix': sys.prefix,
    'base_prefix': sys.base_prefix, 'sys_path': sys.path,
    'venv_config': Path(sys.prefix, 'pyvenv.cfg').read_text(),
    'packages': {d.metadata['Name']: {'version': d.version,
        'location': str(d.locate_file(''))} for d in m.distributions()}
}))
"""
STATE_PROBE = """
import hashlib, json
from pathlib import Path
import joblib
import numpy as np

def state(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return {'float_hex': value.hex()}
    if isinstance(value, np.ndarray):
        return {'dtype': str(value.dtype), 'shape': list(value.shape),
                'values': state(value.tolist())}
    if isinstance(value, np.generic):
        return state(value.item())
    if isinstance(value, np.dtype):
        return {'numpy_dtype': str(value)}
    if isinstance(value, type):
        return {'type': value.__module__ + '.' + value.__qualname__}
    if isinstance(value, dict):
        return {str(key): state(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return {type(value).__name__: [state(item) for item in value]}
    if isinstance(value, bytes):
        return {'bytes_hex': value.hex()}
    name = type(value).__module__ + '.' + type(value).__qualname__
    if hasattr(value, '__dict__'):
        return {'class': name, 'state': state(vars(value))}
    if hasattr(value, '__getstate__'):
        return {'class': name, 'state': state(value.__getstate__())}
    raise TypeError('Unsupported learned state: ' + name)
"""
ARTIFACT_PROBE = (
    STATE_PROBE
    + """
result = {}
for name in ('tree', 'svm', 'most_frequent', 'constant_1', 'selected_model'):
    paths = [Path('/package', folder, name + '.joblib')
             for folder in ('experimento', 'reproduccion')]
    models = [joblib.load(path) for path in paths]
    states = [state(model) for model in models]
    data = [path.read_bytes() for path in paths]
    mismatch = next((i for i, pair in enumerate(zip(*data)) if pair[0] != pair[1]), None)
    result[name] = {
        'learned_state_equal': states[0] == states[1],
        'state_sha256': [hashlib.sha256(json.dumps(item, sort_keys=True,
            allow_nan=False).encode()).hexdigest() for item in states],
        'binary_sha256': [hashlib.sha256(item).hexdigest() for item in data],
        'binary_equal': data[0] == data[1], 'sizes': [len(item) for item in data],
        'first_binary_mismatch': mismatch,
        'mismatch_context_hex': [item[max(0, mismatch-16):mismatch+32].hex()
            for item in data] if mismatch is not None else [],
    }
print(json.dumps(result, allow_nan=False))
"""
)


def load(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive_existing(path):
    if path.exists():
        archive = path.parent / "historial-verificador"
        archive.mkdir(exist_ok=True)
        target = archive / f"{path.stem}-{sha(path)}{path.suffix}"
        if not target.exists():
            shutil.copyfile(path, target)


def inventory(folder):
    return {
        str(path.relative_to(folder)): sha(path)
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def require(condition, message):
    if not condition:
        raise ValueError(message)


def docker_base(root, venv_parent, image):
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid",
        "--env",
        "HOME=/tmp",
        "--workdir",
        "/package/codigo",
    ]
    for source, destination, readonly in (
        (root, "/package", False),
        (root / "codigo", "/package/codigo", True),
        (root / "experimento", "/package/experimento", True),
        (root / "datos", "/package/datos", True),
        (venv_parent, "/repro-env", True),
    ):
        command += [
            "--mount",
            f"type=bind,src={source},dst={destination}" + (",readonly" if readonly else ""),
        ]
    return command + ["--entrypoint", "/repro-env/venv/bin/python", image, "-I", "-B"]


def probe_environment(venv_parent, image, expected, record_path=None):
    # Probing needs only the venv, before codigo/ and datos/ have been created.
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--mount",
        f"type=bind,src={venv_parent},dst=/repro-env,readonly",
        "--entrypoint",
        "/repro-env/venv/bin/python",
        image,
        "-I",
        "-B",
        "-c",
        PROBE,
    ]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    environment = json.loads(result.stdout)
    environment["image"] = json.loads(
        subprocess.run(
            ["docker", "image", "inspect", image], check=True, text=True, capture_output=True
        ).stdout
    )[0]["Id"]
    environment["probe_command"] = command
    environment["clean_venv"] = (
        environment["prefix"] != environment["base_prefix"]
        and "include-system-site-packages = false" in environment["venv_config"].lower()
        and all(
            item["location"].startswith("/repro-env/venv/")
            for item in environment["packages"].values()
        )
        and all(
            path.startswith("/repro-env/venv/")
            for path in environment["sys_path"]
            if "site-packages" in path or "dist-packages" in path
        )
    )
    if record_path is not None:
        archive_existing(record_path)
        write_json(record_path, {"observed_utc": datetime.now(UTC).isoformat(), **environment})
    require(environment["python"] == expected["python"], "Python differs from provenance")
    for name, version in expected.items():
        if name != "python":
            distribution = "scikit-learn" if name == "sklearn" else name
            require(
                environment["packages"][distribution]["version"] == version,
                f"Runtime mismatch: {distribution}",
            )
    require(environment["clean_venv"], "Unclean venv: inherited packages or foreign site-packages")
    return environment


def study_rows(experiment):
    development = [
        row
        for world in load(experiment / "development_transactions.json")["replicas"]
        for row in world["rows"]
        if row["phase"] == "study"
    ]
    final = [
        row
        for row in load(experiment / "final_transactions.json")["rows"]
        if row["phase"] == "study"
    ]
    return {"desarrollo.csv": development, "final.csv": final}


def package(root, venv_parent, image):
    repo = Path(__file__).resolve().parents[1]
    backend = repo / "backend"
    experiment = root / "experimento"
    provenance = load(experiment / "provenance.json")
    report = load(experiment / "aligned_v4_report.json")
    require(report["provenance"] == provenance, "Report/provenance mismatch")
    for key, filename in CODE_PATHS.items():
        require(sha(backend / filename) == provenance["code_sha256"][key], f"Source drift: {key}")
    for name in ("protocol", "calibration"):
        require(
            sha(experiment / f"{name}.json") == provenance[f"{name}_sha256"],
            f"Frozen {name} hash mismatch",
        )
    for name in ("codigo", "datos", "manifest-paquete.json", "reproduccion"):
        require(not (root / name).exists(), f"Refusing to overwrite {root / name}")
    before = inventory(experiment)
    environment = probe_environment(venv_parent, image, provenance["runtime"])
    files = sorted(
        {
            *CODE_PATHS.values(),
            "app/__init__.py",
            "app/db/__init__.py",
            "app/db/base.py",
            *(str(path.relative_to(backend)) for path in (backend / "app/models").glob("*.py")),
        }
    )
    for filename in files:
        target = root / "codigo" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(backend / filename, target)
    (root / "codigo/app/ml/__init__.py").write_text(
        '"""Isolated academic simulation package; no service initialization."""\n',
        encoding="utf-8",
    )
    data = root / "datos"
    data.mkdir()
    for name in ("protocol.json", "calibration.json"):
        shutil.copyfile(experiment / name, data / name)
    counts = {}
    for name, rows in study_rows(experiment).items():
        require(rows and all(row["origen"] == "simulado" for row in rows), "Non-synthetic data")
        with (data / name).open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["origen", *[k for k in rows[0] if k != "origen"]]
            )
            writer.writeheader()
            writer.writerows(rows)
        counts[name] = {"study": len(rows), "unknown": sum(r["late_payment"] is None for r in rows)}
    (root / "requirements.txt").write_text(
        "# Python=="
        + environment["python"]
        + "; Linux; exact installed versions, including pip\n"
        + "".join(
            f"{name}=={value['version']}\n"
            for name, value in sorted(environment["packages"].items())
        ),
        encoding="utf-8",
    )
    shutil.copyfile(Path(__file__).resolve(), root / "reproducir-v4.py")
    write_json(root / "entorno-empaquetado.json", environment)
    require(inventory(experiment) == before, "Experiment changed during packaging")
    manifest = {
        "version": "aligned-v4-self-contained-1",
        "experiment_sha256": before,
        "code_sha256": inventory(root / "codigo"),
        "data_sha256": inventory(data),
        "provenance_code_paths": CODE_PATHS,
        "study_counts": counts,
        "support_sha256": {
            name: sha(root / name)
            for name in ("requirements.txt", "reproducir-v4.py", "entorno-empaquetado.json")
        },
        "isolation": "Only codigo/app/ml/__init__.py is replaced, never a provenance source",
    }
    write_json(root / "manifest-paquete.json", manifest)
    write_readme(root)
    print(
        json.dumps(
            {
                "packaged": str(root),
                "code_files": len(manifest["code_sha256"]),
                "csv": counts,
                "clean_venv": True,
            },
            indent=2,
        )
    )


def normalized_selection(value):
    result = copy.deepcopy(value)
    result.pop("frozen_utc")
    # This hash changes solely because provenance records the new execution time.
    result["decision_sha256"].pop("provenance.json")
    return result


def normalized_report(value):
    result = copy.deepcopy(value)
    result.pop("generated_utc")
    result["provenance"].pop("recorded_utc")
    result["selection"] = normalized_selection(result["selection"])
    require(set(result["artifact_sha256"]) == ARTIFACT_FILES, "Report artifact keys mismatch")
    # Bytes may differ across serialization; validate all actual hashes before loading instead.
    result["artifact_sha256"] = sorted(result["artifact_sha256"])
    return result


def validate_artifact_chains(folder):
    selection = load(folder / "frozen_selection.json")
    manifest = load(folder / "artifact_manifest.json")
    report = load(folder / "aligned_v4_report.json")
    provenance = load(folder / "provenance.json")
    require(set(manifest) == ARTIFACT_FILES, f"Artifact manifest keys mismatch: {folder}")
    require(
        set(report["artifact_sha256"]) == ARTIFACT_FILES, f"Report artifact keys mismatch: {folder}"
    )
    require(set(selection) == SELECTION_KEYS, f"Selection keys mismatch: {folder}")
    require(
        set(selection["decision_sha256"]) == DECISION_FILES, f"Decision keys mismatch: {folder}"
    )
    require(set(selection["families"]) == {"tree", "svm"}, f"Family keys mismatch: {folder}")
    require(
        set(selection["baselines"]) == {"most_frequent", "constant_1"},
        f"Baseline keys mismatch: {folder}",
    )
    choice_keys = {"family", "candidate_index", "params", "threshold", "metrics", "review_policy"}
    for family in ("tree", "svm"):
        choice = selection["families"][family]
        require(set(choice) == choice_keys, f"Candidate keys mismatch: {family}")
        require(
            choice["family"] == choice["params"]["family"] == family, "Candidate family mismatch"
        )
    for family in ("most_frequent", "constant_1"):
        choice = selection["baselines"][family]
        require(
            set(choice) == {"params", "threshold", "metrics", "review_policy"},
            "Baseline schema mismatch",
        )
        require(choice["params"]["family"] == family, "Baseline family mismatch")
    winner = selection["global_winner"]
    require(set(winner) == choice_keys, "Winner keys mismatch")
    require(winner == selection["families"]["svm"], "Frozen V4 winner must be the selected SVM")
    require(
        selection["version"] == "academic-owner-aligned-v4"
        and selection["research_only"] is True
        and selection["feature_names"] == provenance["feature_names"],
        "Selection contract mismatch",
    )
    require(set(report["models"]) == set(MODELS), "Report model keys mismatch")
    require(report["selection"] == selection, "Report/selection mismatch")
    require(report["provenance"] == provenance, "Report/provenance mismatch")
    require(report["artifact_sha256"] == manifest, "Report/artifact manifest mismatch")
    for name in DECISION_FILES:
        require(
            sha(folder / name) == selection["decision_sha256"][name],
            f"Decision SHA256 mismatch: {name}",
        )
    for name in ARTIFACT_FILES:
        require(sha(folder / name) == manifest[name], f"Artifact SHA256 mismatch: {name}")
    require(
        manifest["selected_model.joblib"] == manifest["svm.joblib"],
        "Selected model SHA256 must equal SVM SHA256",
    )
    return True


def compare_reports(expected, actual):
    return {
        "full_report_except_time_and_artifact_serialization": normalized_report(expected)
        == normalized_report(actual),
        "selection": normalized_selection(expected["selection"])
        == normalized_selection(actual["selection"]),
        "raw": {
            f"{model}/{split}": expected["models"][model][split] == actual["models"][model][split]
            for model in MODELS
            for split in SPLITS
        },
        "policy": {
            f"{model}/{split}": expected["models"][model]["review_policy"][split]
            == actual["models"][model]["review_policy"][split]
            for model in MODELS
            for split in SPLITS
        },
        "illustrative_inference": expected["illustrative_inference"]
        == actual["illustrative_inference"],
    }


def all_equal(checks):
    return all(
        all_equal(value) if isinstance(value, dict) else value is True for value in checks.values()
    )


def verify(root, venv_parent=VENV_PARENT, image=IMAGE):
    manifest = load(root / "manifest-paquete.json")
    original, reproduced = root / "experimento", root / "reproduccion"
    expected = load(original / "aligned_v4_report.json")
    actual = load(reproduced / "aligned_v4_report.json")
    checks = compare_reports(expected, actual)
    checks["integrity"] = {
        "frozen_experiment_unchanged": inventory(original) == manifest["experiment_sha256"],
        "packaged_code_unchanged": inventory(root / "codigo") == manifest["code_sha256"],
        "packaged_data_unchanged": inventory(root / "datos") == manifest["data_sha256"],
        **{name: sha(root / name) == value for name, value in manifest["support_sha256"].items()},
        **{
            key: sha(root / "codigo" / path) == expected["provenance"]["code_sha256"][key]
            for key, path in CODE_PATHS.items()
        },
    }
    deterministic = [
        name
        for name in manifest["experiment_sha256"]
        if not name.endswith(".joblib")
        and name
        not in {
            "provenance.json",
            "frozen_selection.json",
            "artifact_manifest.json",
            "aligned_v4_report.json",
        }
    ]
    checks["exact_file_sha256"] = {
        name: sha(original / name) == sha(reproduced / name) for name in deterministic
    }
    checks["decision_and_artifact_chains"] = {}
    for label, folder in (("original", original), ("reproduction", reproduced)):
        checks["decision_and_artifact_chains"][label] = validate_artifact_chains(folder)
    checks["csv_scope"] = {}
    for name, rows in study_rows(original).items():
        with (root / "datos" / name).open(newline="", encoding="utf-8") as stream:
            exported = list(csv.DictReader(stream))
        expected_csv = [
            {key: "" if value is None else str(value) for key, value in row.items()} for row in rows
        ]
        checks["csv_scope"][name] = exported == expected_csv and all(
            row["phase"] == "study" and row["origen"] == "simulado" for row in exported
        )
    inference = load(root / "inferencia-original.json")
    checks["inference_cli"] = {
        "original_equals_reproduction": inference == load(root / "inferencia-reproduccion.json"),
        "equals_frozen_illustration": inference
        == {key: expected["illustrative_inference"][key] for key in inference},
    }
    negative = copy.deepcopy(actual)
    negative["models"]["tree"]["final"]["recall"] += 0.001
    checks["negative_control_detects_metric_mismatch"] = not all_equal(
        compare_reports(expected, negative)
    )
    require(all_equal(checks["integrity"]), "Package integrity failure before artifact loading")
    artifacts = inspect_artifacts(root, venv_parent, image)
    environment = artifacts["environment"]
    checks["environment"] = {
        "current_matches_packaging": environment == load(root / "entorno-empaquetado.json"),
        "current_matches_reproduction": environment == load(root / "entorno-reproduccion.json"),
        "clean_venv": environment["clean_venv"] is True,
        "python_3_12_14": environment["python"] == "3.12.14",
        "inspection_image_pinned_to_probe": environment["image"] in artifacts["command"],
    }
    checks["learned_artifact_state"] = {
        name: value["learned_state_equal"] for name, value in artifacts["models"].items()
    }
    result = {
        "passed": all_equal(checks),
        "methods": {
            "files": (
                "SHA256 byte equality, including datasets, folds, full OOF search, "
                "and final predictions; serialized model bytes reported separately"
            ),
            "metrics": (
                "Exact Python JSON equality; no rounding, epsilon or numeric tolerance; "
                "4 models x 3 splits each raw/policy"
            ),
            "policy": (
                "Entire policy object including daily queues, per-replica counters, "
                "unknowns and capacity"
            ),
            "selection": (
                "Entire frozen decision except frozen_utc and provenance.json hash; "
                "each local hash chain verified"
            ),
            "excluded_time_fields": [
                "report.generated_utc",
                "provenance.recorded_utc",
                "selection.frozen_utc",
            ],
            "derived_hash_exceptions": [
                "selection.decision_sha256.provenance.json",
                "artifact_manifest.frozen_selection.json",
            ],
            "inference": (
                "Separate offline CLI invocations on original and reproduced trusted artifacts, "
                "exact outputs and frozen example"
            ),
            "artifact_state": (
                "Exact recursive comparison of every learned object attribute and native state; "
                "NumPy dtype/shape/logical values, float.hex(), no tolerance; "
                "pickle frames/memoization and array padding are not learned state. "
                "Every local artifact SHA256 verified before trusted deserialization."
            ),
            "artifact_integrity": (
                "Exact six artifact keys in both manifests and reports; exact selection/decision "
                "schema, every actual SHA256 and selected_model == svm checked before joblib.load"
            ),
            "verification_runtime": (
                "Fresh offline probe of the requested image/venv before artifact loading; "
                "must match both historical environments and provenance versions and be clean; "
                "recorded in entorno-verificacion.json; inspection uses the probed image ID"
            ),
            "negative_control": (
                "In-memory +0.001 tree/final/recall must fail the same report comparator; "
                "evidence never edited"
            ),
        },
        "checks": checks,
        "environment": environment,
        "verification_runtime": load(root / "entorno-verificacion.json"),
        "commands": load(root / "comandos-reproduccion.json"),
        "artifact_serialization": artifacts,
        "results": {
            "global_winner": {
                key: actual["selection"]["global_winner"][key]
                for key in ("family", "params", "threshold")
            },
            "development": actual["development"],
            "final": actual["final"],
            "models": {
                name: {
                    "raw": {split: actual["models"][name][split] for split in SPLITS},
                    "policy": {
                        split: actual["models"][name]["review_policy"][split]["metrics"]
                        for split in SPLITS
                    },
                }
                for name in MODELS
            },
            "baseline_comparison": actual["baseline_comparison"],
            "inference": inference,
        },
    }
    archive_existing(root / "verificacion-reproduccion.json")
    write_json(root / "verificacion-reproduccion.json", result)
    require(result["passed"], "Reproduction mismatch; see verificacion-reproduccion.json")
    print(
        json.dumps(
            {
                "passed": True,
                "raw_equalities": 12,
                "policy_equalities": 12,
                "sha256_equalities": len(deterministic),
                "learned_state_equalities": len(checks["learned_artifact_state"]),
                "verification_sha256": sha(root / "verificacion-reproduccion.json"),
                "inference": inference,
            },
            indent=2,
        )
    )
    return result


def reproduce(root, venv_parent, image):
    require(
        not (root / "reproduccion").exists(),
        "Runner requires a nonexisting reproduccion/ directory",
    )
    manifest = load(root / "manifest-paquete.json")
    require(
        inventory(root / "experimento") == manifest["experiment_sha256"], "Frozen evidence drift"
    )
    require(inventory(root / "codigo") == manifest["code_sha256"], "Packaged code drift")
    require(inventory(root / "datos") == manifest["data_sha256"], "Packaged data drift")
    environment = probe_environment(
        venv_parent, image, load(root / "experimento/provenance.json")["runtime"]
    )
    require(
        environment == load(root / "entorno-empaquetado.json"),
        "Environment changed after packaging",
    )
    write_json(root / "entorno-reproduccion.json", environment)
    base = docker_base(root, venv_parent, image)
    runner = "/package/codigo/scripts/academic_credit_aligned_v4.py"
    commands = [
        base
        + [
            runner,
            "--calibration",
            "/package/datos/calibration.json",
            "--protocol",
            "/package/datos/protocol.json",
            "--output-dir",
            "/package/reproduccion",
        ]
    ]
    for label, folder in (("original", "experimento"), ("reproduccion", "reproduccion")):
        require(not (root / f"inferencia-{label}.json").exists(), "Inference output must be new")
        commands.append(
            base
            + [
                runner,
                "--predict-artifact-dir",
                f"/package/{folder}",
                "--input-json",
                "/package/experimento/illustrative_input.json",
                "--output-json",
                f"/package/inferencia-{label}.json",
            ]
        )
    write_json(root / "comandos-reproduccion.json", commands)
    for index, command in enumerate(commands):
        with (root / f"reproduccion-comando-{index + 1}.log").open("x", encoding="utf-8") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    return verify(root, venv_parent, image)


def inspect_artifacts(root, venv_parent, image):
    for folder in ("experimento", "reproduccion"):
        validate_artifact_chains(root / folder)
    environment = probe_environment(
        venv_parent,
        image,
        load(root / "experimento/provenance.json")["runtime"],
        record_path=root / "entorno-verificacion.json",
    )
    require(
        environment == load(root / "entorno-empaquetado.json")
        and environment == load(root / "entorno-reproduccion.json"),
        "Current verification environment drift from recorded packaging/reproduction runtime",
    )
    command = docker_base(root, venv_parent, environment["image"]) + ["-c", ARTIFACT_PROBE]
    result = subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=True,
    )
    models = json.loads(result.stdout)
    require(set(models) == {*MODELS, "selected_model"}, "Learned-state model keys mismatch")
    value = {"models": models, "command": command, "environment": environment}
    archive_existing(root / "estado-artefactos.json")
    write_json(root / "estado-artefactos.json", value)
    return value


def update_tool(root):
    """Explicitly update only packaging tooling, preserving all frozen baselines."""
    path = root / "manifest-paquete.json"
    manifest = load(path)
    for folder, key in (
        ("experimento", "experiment_sha256"),
        ("codigo", "code_sha256"),
        ("datos", "data_sha256"),
    ):
        require(inventory(root / folder) == manifest[key], f"Cannot update tooling: {folder} drift")
    require(
        sha(root / "reproducir-v4.py") == manifest["support_sha256"]["reproducir-v4.py"],
        "Previous tool hash mismatch",
    )
    previous = root / "verificacion-reproduccion.json"
    saved = root / "verificacion-reproduccion-inicial.json"
    if previous.exists() and not saved.exists():
        shutil.copyfile(previous, saved)
    old_hash = manifest["support_sha256"]["reproducir-v4.py"]
    for name in (
        "manifest-paquete.json",
        "reproducir-v4.py",
        "verificacion-reproduccion.json",
        "estado-artefactos.json",
        "entorno-verificacion.json",
    ):
        archive_existing(root / name)
    shutil.copyfile(Path(__file__).resolve(), root / "reproducir-v4.py")
    new_hash = sha(root / "reproducir-v4.py")
    manifest["support_sha256"]["reproducir-v4.py"] = new_hash
    manifest.setdefault("tool_updates", []).append({"old_sha256": old_hash, "new_sha256": new_hash})
    write_json(path, manifest)


def write_readme(root):
    report = load(root / "experimento/aligned_v4_report.json")
    manifest = load(root / "manifest-paquete.json")
    winner = report["selection"]["global_winner"]
    verification = root / "verificacion-reproduccion.json"
    status = "PENDIENTE" if not verification.exists() else str(load(verification)["passed"])
    artifact_path = root / "estado-artefactos.json"
    binary_status = "PENDIENTE"
    if artifact_path.exists():
        binary_status = str(
            all(item["binary_equal"] for item in load(artifact_path)["models"].values())
        )
    rows = []
    for name in MODELS:
        for split in SPLITS:
            raw = report["models"][name][split]
            policy = report["models"][name]["review_policy"][split]
            rows.append(
                f"| {name} | {split} | {raw['n']} | {raw['precision']:.6f} | "
                f"{raw['recall']:.6f} | {raw['f2']:.6f} | "
                f"{policy['metrics']['f2']:.6f} | {policy['reviews']} |"
            )
    path = root / "README.md"
    previous = path.read_text(encoding="utf-8") if path.exists() else "# APF3 V4\n"
    text = previous.split(README_MARKER)[0].rstrip() + "\n\n" + README_MARKER + "\n"
    text += f"""
## Paquete Autocontenido

**100% sintetico. Solo investigacion academica; NO produccion ni aprobacion crediticia.**
La fuente es una declaracion parcial del propietario Rildo: recuerdo y revision
parcial de cuaderno, aproximada y no auditada independientemente. Los 48 apuntes
(45 evaluables, 8 atrasos, 3 desconocidos) son anclas agregadas, NO filas de
entrenamiento ni validacion real. No se incluye el DOCX privado; solo su hash y
anclas agregadas. Distribuciones, poblacion, calendario, F2 y tiempos de revision
son hipotesis declaradas. El formulario hipotetico anterior queda excluido.

- `experimento/`: 24 archivos congelados originales; no sobrescribir.
- `codigo/`: fuentes copiadas byte a byte del backend y cotejadas con provenance.
- `codigo/app/ml/__init__.py`: unica sustitucion, inicializador aislado sin servicio legacy.
- Los modelos SQLAlchemy y `app/db/base.py` solo resuelven imports; no se conecta una DB.
- `datos/protocol.json` y `datos/calibration.json`: bytes exactos de la evidencia congelada.
- `datos/desarrollo.csv` y `datos/final.csv`: TODOS los fiados concedidos de estudio,
  con `origen=simulado`, incluidos desconocidos; sin warmup. Se conservan todas las columnas.
- `requirements.txt`: todas las versiones realmente instaladas en el venv Linux, fijadas.
- `manifest-paquete.json`: SHA256 de fuentes, datos y evidencia; integridad, no firma.
- `reproducir-v4.py`: herramienta independiente de la biblioteca estandar; no necesita el repo.
- `reproduccion/`: ejecucion nueva, separada, sin retocar protocolo, grilla, semillas ni umbrales.
- `verificacion-reproduccion.json`: metodos, igualdades, cadenas de hashes, entorno y resultados.

Conteos CSV: `{json.dumps(manifest["study_counts"], sort_keys=True)}`.
Las replicas son historias alternativas del mismo negocio, no sucursales simultaneas
ni volumen real sumable. El JSON transaccional conserva warmup para auditar snapshots,
pero nunca se exporta como fila de estudio. Entrenamiento y OOF usan solo labels resueltos;
la cola final incluye desconocidos para competir por capacidad, sin inventar labels.

## Reproduccion Limpia

Estado de verificacion: **{status}**. Python exacto `3.12.14`; Linux ARM64 en esta ejecucion.
Imagen usada: `{IMAGE}`. Su ID y el inventario del venv constan en `entorno-*.json`.
El venv existente tiene `include-system-site-packages = false`; todas sus distribuciones
proceden de `/repro-env/venv/`. No se usa el Python cientifico global de la imagen.

Desde este directorio, con Docker local y el venv Linux preparado:

```sh
VENV_PARENT={VENV_PARENT}
python3 reproducir-v4.py --root "$PWD" --action reproduce \\
  --image {IMAGE} --venv-parent "$VENV_PARENT"
python3 reproducir-v4.py --root "$PWD" --action verify
```

El primer comando SOLO se ejecuta cuando `reproduccion/` no existe. No borrar ni
reutilizar evidencia para repetirlo: usar otra copia del paquete sin salidas de reproduccion.
El segundo vuelve a verificar la salida existente, sin entrenar. Cualquier diferencia
o archivo faltante termina con codigo distinto de cero y guarda el fallo en el JSON.
`comandos-reproduccion.json` contiene los tres comandos Docker exactos ejecutados.
Se usa `--network none`, raiz del contenedor readonly, codigo/datos/experimento/venv
montados readonly, `-I -B` y sin privilegios adicionales; solo las salidas del paquete
y `/tmp` son escribibles. No se instala ni descarga nada durante esta reproduccion.

Para preparar OTRO venv Linux desde cero (requiere paquetes disponibles previamente,
NO forma parte de la reproduccion sin red): Python 3.12.14, `python -m venv venv`
y `venv/bin/python -m pip install -r requirements.txt`. Para instalacion offline usar
`--no-index --find-links /ruta/wheels`; los wheels y la imagen NO se distribuyen aqui.
El paquete es autocontenido en fuentes/datos/evidencia, no un sistema operativo ni
un archivo de dependencias binarias. No se ha creado ZIP.

## Resultados

Familia seleccionada: `{winner["family"]}`, umbral `{winner["threshold"]}`.
Parametros: `{json.dumps(winner["params"], sort_keys=True)}`.
Las cifras siguientes proceden de la evidencia original; cuando la verificacion
es True coinciden exactamente con la reproduccion, antes de redondear para esta tabla.

| Modelo | Split | n conocido | Precision raw | Recall raw | F2 raw | F2 policy | Revisiones |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
"""
    text += "\n".join(rows) + "\n\n"
    proposal_pass = report["baseline_comparison"]["final"]["proposal_pass"]
    text += f"""Propuesta frente a ambos Dummy en final: `{proposal_pass}`.
Inferencia ilustrativa: p=`{report["illustrative_inference"].get("probability")}`,
clase=`{report["illustrative_inference"].get("predicted")}`; sin etiqueta conocida,
no es una aprobacion ni una decision de cola diaria.

Se exige igualdad exacta de datasets, folds exteriores/interiores, busqueda OOF,
seleccion, predicciones y 12 pares raw + 12 pares policy completos (4 modelos x
train/OOF/final), mas inferencia CLI independiente con ambos artefactos.
No hay tolerancia numerica. Se excluyen los tres timestamps de ejecucion y los
hashes que derivan de ellos; cada cadena local se valida igualmente. Igualdad
binaria de los `.joblib`: **{binary_status}**. Se exige por separado igualdad de los
cinco estados aprendidos completos (atributos, arrays con dtype/shape/valores y
floats hexadecimales). Si la verificacion es True, estos estados coinciden aunque
la representacion serializada sea diferente. Se verifica en Docker sin red, sin
entrenar ni regenerar datos; comando, hashes, tamanos y primeros offsets distintos
quedan en `estado-artefactos.json`. No se equipara igualdad funcional con igualdad
binaria. La primera verificacion estricta fallida se conserva en
`verificacion-reproduccion-inicial.json`, si existe. Un control negativo altera
recall solo en memoria y debe detectar la discrepancia.

## Limites

No demuestra prediccion real, ahorro medido, capacidad operativa ni seguridad en
produccion. OOF se reutiliza para seleccionar hiperparametros/umbral y es optimista;
la calibracion interna de probabilidades NO es evaluacion anidada de seleccion.
La cola OOF no incluye desconocidos y no reproduce su competencia por capacidad.
Tope 5/dia por replica y fecha civil de Lima; dos minutos por caso es una hipotesis,
no tiempo medido ni todas las tareas humanas. Se conserva cualquier fallo de auditoria
final o de comparacion con baselines, sin regenerar ni ajustar.
Los `.joblib` son ejecutables: cargar solo artefactos locales confiables; los hashes
detectan cambios, no garantizan confianza en su publicador. No se modifico el backend
runtime ni se generaron figuras, informe o sustentacion con este empaquetador.
"""
    path.write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument(
        "--action",
        choices=("package", "reproduce", "verify", "inspect-artifacts", "update-tool"),
        default="package",
    )
    parser.add_argument("--venv-parent", type=Path, default=VENV_PARENT)
    parser.add_argument("--image", default=IMAGE)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    verification = root / "verificacion-reproduccion.json"
    runtime = root / "entorno-verificacion.json"
    previous_verification = sha(verification) if verification.is_file() else None
    previous_runtime = sha(runtime) if runtime.is_file() else None
    try:
        require(root.is_dir(), "Package root must already exist")
        if args.action == "package":
            package(root, args.venv_parent.resolve(), args.image)
        elif args.action == "reproduce":
            reproduce(root, args.venv_parent.resolve(), args.image)
        elif args.action == "inspect-artifacts":
            print(
                json.dumps(
                    inspect_artifacts(root, args.venv_parent.resolve(), args.image), indent=2
                )
            )
        elif args.action == "update-tool":
            update_tool(root)
        else:
            verify(root, args.venv_parent.resolve(), args.image)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        if root.is_dir() and args.action in ("reproduce", "verify"):
            if (
                not verification.exists()
                or sha(verification) == previous_verification
                or load(verification).get("passed") is not False
            ):
                archive_existing(verification)
                failure = {"passed": False, "error": str(error)}
                if runtime.exists() and sha(runtime) != previous_runtime:
                    failure["verification_runtime"] = load(runtime)
                write_json(verification, failure)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
