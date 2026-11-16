"""Prepare a trusted V6 web bundle using bytes and stdlib only, never pickle/ML."""

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path

VERSION = "academic-owner-pending-v6"
REPORT = "pending_v6_report.json"
FILES = (
    REPORT,
    "frozen_selection.json",
    "selected_model.joblib",
    "illustrative_input.json",
    "provenance.json",
)
EXPERIMENT_FILES = {
    "artifact_manifest.json",
    "calibration.json",
    "constant_1.joblib",
    "cv_search.json",
    "data_protocol.json",
    "development_audits.json",
    "development_gate.json",
    "development_rows.csv",
    "development_rows.json",
    "development_study_rows.json",
    "development_transactions.json",
    "final_audits.json",
    "final_call_ledger.json",
    "final_predictions.csv",
    "final_predictions.json",
    "final_rows.csv",
    "final_transactions.json",
    "fold_audit.json",
    "freeze_before_final.json",
    "frozen_selection.json",
    "historical_snapshot.json",
    "illustrative_input.json",
    "illustrative_output.json",
    "inputdev_APF3_OWNER_ANCHORS_V4.json",
    "inputdev_APF3_OWNER_REVIEW_V5.json",
    "inputdev_APF3_PENDING_V6_DATA_PROTOCOL.json",
    "inputdev_PND6-D1_transactions.json",
    "inputdev_PND6-D2_transactions.json",
    "inputdev_README.md",
    "inputdev_data_revision_report.json",
    "inputdev_desarrollo.csv",
    "inputdev_desarrollo_etiquetado.csv",
    "inputdev_development_audits.json",
    "inputdev_inventory.json",
    "inputdev_manifest.json",
    "inputdev_preparation_plan.json",
    "inputdevmanifest.json",
    "most_frequent.joblib",
    "owner_review.json",
    REPORT,
    "protocol.json",
    "provenance.json",
    "selected_model.joblib",
    "snapshot_APF3_OWNER_ANCHORS_V4.json",
    "snapshot_APF3_OWNER_REVIEW_V5.json",
    "snapshot_APF3_PENDING_V6_DATA_PROTOCOL.json",
    "snapshot_APF3_PENDING_V6_MODEL_PROTOCOL.json",
    "snapshot_README.md",
    "snapshot_calidad-dev-v6.csv",
    "snapshot_inventory.json",
    "snapshot_manifest.json",
    "snapshot_pliegues-planificados.json",
    "snapshot_preparation_plan.json",
    "snapshot_summaryauditoria-dev-v6.json",
    "svm.joblib",
    "training_reports.json",
    "tree.joblib",
}
RUNTIME = {
    "python": "3.12.14",
    "sklearn": "1.9.1",
    "numpy": "2.5.3",
    "scipy": "1.18.1",
    "joblib": "1.6.0",
}
ILLUSTRATIVE = {
    "completed_sales": 6,
    "paid_credits": 6,
    "paid_late": 1,
    "pending_overdue": 0,
    "pending_current": 0,
    "outstanding": 0,
    "utilization": 0,
    "requested_ratio": 0.25,
    "tenure_days": 60,
    "punctuality_rate": 0.8333333333333334,
    "overdue_rate": 0,
}
SELECTION_METRIC = "OOF F2 of held-out capped review actions on known labels, beta=2"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_path(path):
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        require(not part.is_symlink(), f"Symlink forbidden: {part}")
    return path


def read_bytes(path):
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), f"Not a regular file: {path}")
        return stream.read()


def object_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"Nonfinite JSON: {value}")

    result = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)
    require(isinstance(result, dict), "Expected JSON object")
    return result


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(source, destination):
    source, destination = safe_path(source), safe_path(destination)
    require(source.is_dir(), "Package directory missing")
    require(not destination.exists(), "Destination must be a new directory; never overwrite")
    require(not destination.is_relative_to(source), "Destination cannot be inside the package")
    manifest = object_json(read_bytes(source / "manifest-paquete.json"))
    require(manifest["version"] == "pending-v6-delivery-1", "Invalid package version")
    folders = manifest["folders"]
    require(isinstance(folders, dict), "Missing folder hashes")
    hashes = folders["experimento"]
    require(isinstance(hashes, dict), "Missing experimento hashes")
    require(
        manifest.get("original_experiment_sha256") == hashes,
        "Experiment hashes differ between manifest sections",
    )
    require(
        set(hashes) == EXPERIMENT_FILES,
        "Expected exactly 57 frozen experiment hashes including the five web inputs",
    )
    contents = {}
    for name, expected in hashes.items():
        require(
            isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
            f"Invalid SHA256: {name}",
        )
        data = read_bytes(source / "experimento" / name)
        require(sha(data) == expected, f"SHA256 mismatch: {name}")
        contents[name] = data
    report, frozen, provenance, protocol, artifacts = (
        object_json(contents[name])
        for name in (
            REPORT,
            "frozen_selection.json",
            "provenance.json",
            "protocol.json",
            "artifact_manifest.json",
        )
    )
    require(
        report["version"] == frozen["version"] == VERSION, "Version mismatch"
    )
    require(
        isinstance(protocol["version"], str) and protocol["version"].startswith(VERSION),
        "Model protocol version mismatch",
    )
    require(
        report["origen"] == "simulado"
        and report["research_only"] is True
        and frozen["research_only"] is True
        and report["business_approval"] is False,
        "Bundle must be synthetic research, never business approval",
    )
    require(
        report["selection"] == frozen and report["provenance"] == provenance,
        "Report selection/provenance mismatch",
    )
    require(
        report["feature_names"]
        == frozen["feature_names"]
        == protocol["feature_names"]
        == list(ILLUSTRATIVE),
        "Feature contract mismatch",
    )
    require(
        {key: provenance["runtime"].get(key) for key in RUNTIME} == RUNTIME
        and {key: protocol["runtime"].get(key) for key in RUNTIME} == RUNTIME,
        "Pinned runtime mismatch",
    )
    require(report["artifact_sha256"] == artifacts, "Report artifact manifest mismatch")
    for mapping in (artifacts, frozen["decision_sha256"]):
        require(bool(mapping), "Empty frozen hashes")
        for name, expected in mapping.items():
            require(name in hashes and hashes[name] == expected, f"Frozen hash mismatch: {name}")
    for name in ("selected_model.joblib", "frozen_selection.json"):
        require(artifacts.get(name) == hashes[name], f"Missing artifact hash: {name}")
    for name in ("protocol.json", "calibration.json", "provenance.json"):
        require(
            frozen["decision_sha256"].get(name) == hashes[name], f"Missing decision hash: {name}"
        )
    winner = frozen["global_winner"]
    require(winner["family"] == winner["params"]["family"] == "tree", "Winner must be tree")
    require(
        winner["threshold"] == report["models"]["tree"]["threshold"] == 0.2,
        "Frozen threshold mismatch",
    )
    require(
        hashes["selected_model.joblib"] == hashes["tree.joblib"],
        "Selected model must be the frozen tree, not the SVM or another family",
    )
    require(
        artifacts.get("selected_model.joblib") == artifacts.get("tree.joblib"),
        "Artifact manifest must bind selected_model.joblib to tree.joblib",
    )
    require(
        protocol["selection"]["primary"] == SELECTION_METRIC,
        "Frozen selection metric mismatch",
    )
    illustrative = object_json(contents["illustrative_input.json"])
    require(set(illustrative) == {"features"}, "Unexpected illustrative input fields")
    features = illustrative["features"]
    require(
        isinstance(features, dict)
        and features == protocol["illustrative_input"]["features"] == ILLUSTRATIVE
        and all(type(value) in (int, float) for value in features.values()),
        "Illustrative input must match the exact frozen protocol example",
    )
    cap = provenance["source_anchors"]["client_cap_pen"]
    require(
        type(cap) in (int, float)
        and cap == 80
        and features["requested_ratio"] * cap == 20
        and features["outstanding"] + 20 <= cap,
        "Expected PEN 20 within PEN 80 cap",
    )

    # Validate everything before creating even the ignored local parent directory.
    missing = []
    parent = destination.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    require(parent.is_dir(), "Destination parent is not a directory")
    for parent in reversed(missing):
        safe_path(parent).mkdir()
    safe_path(destination).mkdir()
    for name in FILES:
        with (destination / name).open("xb") as stream:
            stream.write(contents[name])
    web_manifest = {"version": VERSION, "files": {name: hashes[name] for name in FILES}}
    with (destination / "web_manifest.json").open("x", encoding="ascii") as stream:
        stream.write(json.dumps(web_manifest, indent=2) + "\n")
    require(
        {item.name for item in destination.iterdir()} == set(FILES) | {"web_manifest.json"},
        "Unexpected output files",
    )
    for name in FILES:
        require(sha(read_bytes(destination / name)) == hashes[name], f"Copy mismatch: {name}")
    return {
        "destination": str(destination),
        "experiment_hashes_checked": len(hashes),
        "copied_files": list(FILES),
        "web_manifest": web_manifest,
        "checks": {
            "frozen_consistency": True,
            "pinned_runtime": True,
            "tree": True,
            "research_only": True,
            "business_approval": False,
            "illustrative_pen": 20,
            "cap_pen": cap,
            "exact_output_files": True,
            "model_loaded": False,
            "inference_executed": False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Trusted extracted V6 delivery")
    parser.add_argument("--destination", type=Path, default=Path("academic/v6"))
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.destination)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Preparation refused: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
