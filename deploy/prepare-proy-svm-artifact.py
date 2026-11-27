"""Copy the pinned, trusted P0-05 freeze without training or deserialization (stdlib only)."""

import argparse
import hashlib
import json
from pathlib import Path

PINS = {
    "selected_model.joblib": "f89db794fc657c3c0f858b1392e26474bc15577facd38ac49355b19a6834db45",
    "svm.joblib": "f89db794fc657c3c0f858b1392e26474bc15577facd38ac49355b19a6834db45",
    "artifact_manifest.json": "874c246559a545fad231b1a457fa71f09fe677a60c34bb54ee5962f4e9e063f2",
    "frozen_selection.json": "90548dcfc7562cf01a8175df99bd4884eee042c473b11818e7210afdec3d046c",
    "provenance.json": "a738b147775b574a968dfac55dbe5cd07f5f2b39bf57accac78be2e09703d4ee",
    "freeze_before_final.json": "08ffb6bcdf8f23724b3436f7835481a4951996e9cfe199d6fa2fb5e51f7f013e",
    "PROY_P0-05_MODEL_PROTOCOL.json": "b345352ae4c6539de9abfa0c6e40bdff3ec528ef966b95711d2631cdd50e14c0",
}
MODEL_NAME = "credit_proy_svm_v1.joblib"
META_NAME = "credit_proy_svm_v1_meta.json"
COMPATIBILITY_SHA256 = "3daed68193f3cd328949e3b2412646394f1a82b6580bc094665107422924aa30"


def prepare(source: Path, artifact_dir: Path, compatibility_record: Path | None = None) -> None:
    if not artifact_dir.is_dir() or artifact_dir.is_symlink():
        raise ValueError("Artifact directory must already exist and not be a symlink")
    targets = [artifact_dir / MODEL_NAME, artifact_dir / META_NAME]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise ValueError("Refusing to overwrite an existing artifact or metadata")
    record_path = compatibility_record or (
        Path(__file__).resolve().parents[1] / "docs/PROY_SVM_COMPATIBILIDAD.json"
    )
    if record_path.is_symlink() or not record_path.is_file():
        raise ValueError("Missing trusted compatibility evidence")
    record_bytes = record_path.read_bytes()
    if hashlib.sha256(record_bytes).hexdigest() != COMPATIBILITY_SHA256:
        raise ValueError("Compatibility evidence SHA256 mismatch")
    record = json.loads(record_bytes)
    if (record["compatible"] is not True or record["learned_state_unchanged"] is not True
            or record["artifact_sha256"] != PINS["selected_model.joblib"]):
        raise ValueError("Model compatibility not verified")
    contents = {}
    for name, digest in PINS.items():
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Source must be a regular non-symlink file: {name}")
        contents[name] = path.read_bytes()
        if hashlib.sha256(contents[name]).hexdigest() != digest:
            raise ValueError(f"Source SHA256 mismatch: {name}")
    manifest = json.loads(contents["artifact_manifest.json"])
    freeze = json.loads(contents["freeze_before_final.json"])
    selection = json.loads(contents["frozen_selection.json"])
    provenance = json.loads(contents["provenance.json"])
    for name in ("selected_model.joblib", "svm.joblib", "frozen_selection.json"):
        if manifest[name] != PINS[name] or freeze["files"][name] != PINS[name]:
            raise ValueError("Inconsistent frozen manifest")
    if (
        freeze["final_generation_calls"] != 0
        or freeze["final_prediction_calls"] != 0
        or provenance["authorization"]
        != {"stage": "dev_only_selection", "final_contacted": False}
        or selection["global_winner"]["family"] != "svm"
        or selection["global_winner"]["threshold"] != 0.1
    ):
        raise ValueError("Not an authorized development-only SVM freeze")
    meta = {
        "artifact_name": MODEL_NAME,
        "artifact_sha256": PINS["selected_model.joblib"],
        "model_version": "credit-proy-svm-v1",
        "source_version": selection["version"],
        "schema_version": "proy-credit-contract-v1",
        "feature_names": selection["feature_names"],
        "family": "svm",
        "threshold": 0.1,
        "runtime": provenance["runtime"],
        "frozen_selection_sha256": PINS["frozen_selection.json"],
        "source_provenance_sha256": PINS["provenance.json"],
        "protocol_sha256": PINS["PROY_P0-05_MODEL_PROTOCOL.json"],
        "source": "academic/proy-p05",
        "source_files_sha256": PINS,
        "provenance": provenance,
        "research_only": True,
        "business_approval": False,
        "public": True,
        "final_contacted": False,
        "final_test_evaluated": False,
        "stage": "dev_only_selection",
        "compatibility": {
            "status": "experimentally_verified_for_exact_runtime_tuples_only",
            "evidence_sha256": COMPATIBILITY_SHA256,
            "tested_runtimes": record["tested_runtime_whitelist"],
            "production_authorized": False,
        },
        "training_domain": {
            "completed_sales_equals_paid_credits": True,
            "requested_ratio_min": 5 / 80,
            "requested_ratio_max": 50 / 80,
            "reference_cap_soles": 80,
            "not_a_business_limit": True,
        },
    }
    with targets[0].open("xb") as stream:
        stream.write(contents["selected_model.joblib"])
    with targets[1].open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(meta, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=root / "entregables/PROY_Grupo2/materiales/experiment/p0-05",
    )
    parser.add_argument(
        "--artifact-dir", type=Path, default=root / "backend/app/ml/artifacts"
    )
    parser.add_argument("--compatibility-record", type=Path,
                        default=root / "docs/PROY_SVM_COMPATIBILIDAD.json")
    args = parser.parse_args()
    prepare(args.source, args.artifact_dir, args.compatibility_record)
