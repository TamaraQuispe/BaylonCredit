"""Retune using old train/validation only, then evaluate once on a new synthetic cohort."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import joblib
import sklearn

from app.ml.academic_experiment import (
    MIN_RECALL,
    THRESHOLDS,
    build_candidates,
    error_analysis,
    matrix,
    metrics,
    select_validation_candidate,
)
from app.ml.features import FEATURE_NAMES
from app.ml.synthetic import generate_academic_dataset, validate_academic_dataset

FINAL_SEED = 20261030
FINAL_CLIENTS = 120
MODEL_SEED = 42


def run(source: Path, output: Path) -> dict:
    if output.resolve().is_relative_to(Path(__file__).resolve().parents[1] / "app"):
        raise ValueError("Academic outputs must remain outside production app")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Output must be empty; do not overwrite experiment evidence")
    original_report = json.loads((source / "academic_synthetic_report.json").read_text())
    ledger_path = source / "synthetic_transactions.json"
    assert (
        hashlib.sha256(ledger_path.read_bytes()).hexdigest()
        == original_report["sha256"][ledger_path.name]
    )
    original = json.loads(ledger_path.read_text())
    validate_academic_dataset(original)
    train = [r for r in original["rows"] if r["split"] == "train" and r["late_payment"] is not None]
    validation = [
        r for r in original["rows"] if r["split"] == "validation" and r["late_payment"] is not None
    ]
    assert not ({r["client_id"] for r in train} & {r["client_id"] for r in validation})
    protocol = {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "data_source": "synthetic",
        "training_source_sha256": original_report["sha256"],
        "old_test_policy": "Excluded from selection; previously published, not a fresh final test",
        "models": list(build_candidates(MODEL_SEED)),
        "thresholds": THRESHOLDS,
        "selection": (
            "Highest validation accuracy with recall >= 0.30; balanced accuracy/F1 tie breaks"
        ),
        "recall_floor": MIN_RECALL,
        "cost_assumption": "FP and FN equally weighted for accuracy; not business cost estimates",
        "final_cohort_seed": FINAL_SEED,
        "final_cohort_clients": FINAL_CLIENTS,
        "generator_changes": "None; same coherent simulator as academic execution-02",
        "deployment": "Read-only academic demonstration only; no credit decisions or production",
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "generator_sha256": hashlib.sha256(
            (Path(__file__).resolve().parents[1] / "app/ml/synthetic.py").read_bytes()
        ).hexdigest(),
    }
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    previous_model = joblib.load(source / "academic_synthetic_late_payment.joblib")
    x_train, y_train = matrix(train)
    x_validation, y_validation = matrix(validation)
    validation_errors = error_analysis(
        validation, previous_model.predict_proba(x_validation)[:, 1], 0.5
    )
    (output / "first_model_validation_errors.json").write_text(
        json.dumps(validation_errors, indent=2) + "\n"
    )
    candidates = build_candidates(MODEL_SEED)
    search = []
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        probability = model.predict_proba(x_validation)[:, 1]
        for threshold in THRESHOLDS:
            search.append(
                {
                    "model": name,
                    "threshold": threshold,
                    "metrics": metrics(y_validation, probability, threshold),
                }
            )
    chosen = select_validation_candidate(search)
    frozen = {"frozen_utc": datetime.now(UTC).isoformat(), **chosen}
    (output / "frozen_selection.json").write_text(json.dumps(frozen, indent=2) + "\n")
    (output / "validation_search.json").write_text(json.dumps(search, indent=2) + "\n")
    # The final cohort is generated only after the choice is persisted above.
    fresh = generate_academic_dataset(FINAL_CLIENTS, FINAL_SEED)
    validate_academic_dataset(fresh)
    for client in fresh["clients"]:
        client["client_id"] = client["client_id"].replace("SYN-C", "FINAL-C")
        client["split"] = "final_test"
    for group in (fresh["loans"], fresh["sales"], fresh["rows"]):
        for row in group:
            row["client_id"] = row["client_id"].replace("SYN-C", "FINAL-C")
            if "loan_id" in row:
                row["loan_id"] = row["loan_id"].replace("SYN-L", "FINAL-L")
            if "split" in row:
                row["split"] = "final_test"
    final_checks = validate_academic_dataset(fresh)
    final_rows = [r for r in fresh["rows"] if r["late_payment"] is not None]
    assert not ({r["client_id"] for r in original["rows"]} & {r["client_id"] for r in final_rows})
    x_final, y_final = matrix(final_rows)
    selected_model = candidates[chosen["model"]]
    probability = selected_model.predict_proba(x_final)[:, 1]
    prior = float(y_train.mean())
    comparison = {
        "second_model": metrics(y_final, probability, chosen["threshold"]),
        "first_model_same_fresh_cohort": metrics(
            y_final, previous_model.predict_proba(x_final)[:, 1], 0.5
        ),
        "majority_baseline": metrics(y_final, [prior] * len(y_final), 0.5),
    }
    with (output / "fresh_synthetic_predictions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "data_source",
                "client_id",
                "loan_id",
                "actual_late_payment",
                "predicted_late_payment",
                "estimated_probability",
            ]
        )
        for row, risk in zip(final_rows, probability, strict=True):
            writer.writerow(
                [
                    "synthetic",
                    row["client_id"],
                    row["loan_id"],
                    row["late_payment"],
                    int(risk >= chosen["threshold"]),
                    float(risk),
                ]
            )
    (output / "fresh_synthetic_transactions.json").write_text(json.dumps(fresh, indent=2) + "\n")
    final_errors = error_analysis(final_rows, probability, chosen["threshold"])
    (output / "final_errors_not_for_tuning.json").write_text(
        json.dumps(final_errors, indent=2) + "\n"
    )
    joblib.dump(selected_model, output / "academic_model_v2.joblib")
    report = {
        "version": "academic-synthetic-late-v2",
        "data_source": "synthetic",
        "generated_utc": datetime.now(UTC).isoformat(),
        "protocol": protocol,
        "target": "late_payment",
        "feature_names": FEATURE_NAMES,
        "chosen": chosen,
        "training_rows": len(train),
        "validation_rows": len(validation),
        "fresh_final_checks": final_checks,
        "final_labeled_rows": len(final_rows),
        "comparison_on_same_fresh_cohort": comparison,
        "limitations": [
            "Single synthetic generator, not external real-world validation",
            "Final cohort must not be reused for more tuning",
            "Probabilities not calibrated for real customers",
            "Prior experiment already inspected old test; it was excluded here",
            "Read-only academic lab eligible, never automatic credit approval",
        ],
        "artifact_sha256": hashlib.sha256(
            (output / "academic_model_v2.joblib").read_bytes()
        ).hexdigest(),
    }
    (output / "experiment_v2_report.json").write_text(json.dumps(report, indent=2) + "\n")
    lab_cases = []
    seen = set()
    for row in final_rows:
        key = (row["scenario"], row["paid_credits"] == 0)
        if key in seen:
            continue
        seen.add(key)
        lab_cases.append(
            {
                "id": row["loan_id"],
                "scenario": row["scenario"],
                "requested_amount": row["requested_amount"],
                "due_date": row["due_date"],
                "actual_late_payment": row["late_payment"],
                "features": {name: row[name] for name in FEATURE_NAMES},
            }
        )
    (output / "academic_lab_cases.json").write_text(
        json.dumps({"data_source": "synthetic", "cases": lab_cases}, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "selected": chosen["model"],
                "threshold": chosen["threshold"],
                "fresh_final_comparison": comparison,
            },
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output_dir)
