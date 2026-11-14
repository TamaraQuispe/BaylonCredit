"""Inspect a trusted, frozen synthetic artifact without training or application access."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Exact MVP FEATURE_NAMES, kept standalone to avoid importing database/application code.
FEATURE_NAMES = [
    "completed_sales",
    "paid_credits",
    "paid_late",
    "pending_overdue",
    "pending_current",
    "outstanding",
    "utilization",
    "requested_ratio",
    "tenure_days",
    "punctuality_rate",
    "overdue_rate",
]
ILLUSTRATIVE_FEATURES = dict(
    zip(FEATURE_NAMES, [3, 2, 1, 0, 0, 0, 0, 0.25, 45, 0.5, 0], strict=True)
)


def validate_features(features: object) -> dict[str, float]:
    if not isinstance(features, dict) or set(features) != set(FEATURE_NAMES):
        raise ValueError("Input must be an object with exactly the 11 FEATURE_NAMES keys")
    values = {}
    for name in FEATURE_NAMES:
        value = features[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite JSON number, not bool/string")
        try:
            value = float(value)
        except OverflowError as exc:
            raise ValueError(f"{name} must be finite") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")
        if name in FEATURE_NAMES[:5] + ["tenure_days"] and not value.is_integer():
            raise ValueError(f"{name} must be integral")
        if name in ("utilization", "requested_ratio", "punctuality_rate", "overdue_rate"):
            if value > 1:
                raise ValueError(f"{name} must be in [0, 1]")
        values[name] = value
    if values["requested_ratio"] <= 0:
        raise ValueError("requested_ratio must be greater than zero")
    paid, late = values["paid_credits"], values["paid_late"]
    if late > paid:
        raise ValueError("paid_late cannot exceed paid_credits")
    punctuality = (paid - late) / paid if paid else 0.0
    active = values["pending_overdue"] + values["pending_current"]
    overdue = values["pending_overdue"] / active if active else 0.0
    for name, expected in (("punctuality_rate", punctuality), ("overdue_rate", overdue)):
        if not math.isclose(values[name], expected, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(f"{name} is inconsistent with the supplied counts")
    return values


def inspect_artifact(artifact_dir: Path, input_json: Path | None = None) -> dict:
    report_path = artifact_dir / "experiment_v2_report.json"
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    if report["feature_names"] != FEATURE_NAMES:
        raise ValueError("Report feature_names must exactly match FEATURE_NAMES in order")
    if report["chosen"]["threshold"] != 0.4:
        raise ValueError("Expected the frozen original threshold 0.4; no reselection allowed")
    if report["data_source"] != "synthetic" or report["target"] != "late_payment":
        raise ValueError("Expected the synthetic late_payment academic report")

    features = validate_features(
        json.loads(input_json.read_text(encoding="utf-8"))
        if input_json is not None
        else ILLUSTRATIVE_FEATURES
    )
    cases = json.loads((artifact_dir / "academic_lab_cases.json").read_text(encoding="utf-8"))
    if any(features == case["features"] for case in cases["cases"]):
        raise ValueError(
            "Input matches a predefined case; only a new illustrative vector is allowed"
        )

    artifact_path = artifact_dir / "academic_model_v2.joblib"
    artifact_bytes = artifact_path.read_bytes()
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    if digest != report["artifact_sha256"]:
        raise ValueError("Artifact SHA256 mismatch; refusing joblib.load")
    # Deserialize the verified snapshot, not a potentially changed file. Trust is still required.
    model = joblib.load(io.BytesIO(artifact_bytes))
    if not isinstance(model, Pipeline) or len(model.steps) != 2:
        raise ValueError("Expected exactly a StandardScaler + LogisticRegression pipeline")
    scaler, classifier = (step for _, step in model.steps)
    if not isinstance(scaler, StandardScaler) or not isinstance(classifier, LogisticRegression):
        raise ValueError("Expected StandardScaler followed by LogisticRegression")
    if not scaler.with_mean or not scaler.with_std:
        raise ValueError("Expected centered and standardized features")
    if not np.array_equal(model.classes_, [0, 1]):
        raise ValueError("Expected ordered classes [0, 1]")
    if (
        model.n_features_in_ != 11
        or classifier.n_features_in_ != 11
        or classifier.coef_.shape != (1, 11)
        or classifier.intercept_.shape != (1,)
        or scaler.mean_.shape != (11,)
        or scaler.scale_.shape != (11,)
    ):
        raise ValueError("Fitted pipeline dimensions do not match the 11-feature schema")
    if not all(
        np.isfinite(array).all()
        for array in (classifier.coef_, classifier.intercept_, scaler.mean_, scaler.scale_)
    ) or not (scaler.scale_ > 0).all():
        raise ValueError("Pipeline parameters must be finite with positive scales")
    if hasattr(model, "feature_names_in_") and list(model.feature_names_in_) != FEATURE_NAMES:
        raise ValueError("Pipeline feature names differ from the report")

    coefficients = [
        {
            "feature": name,
            "standardized_coefficient": float(coefficient),
            "odds_ratio_exp_coefficient": math.exp(float(coefficient)),
            "scaler_mean": float(mean),
            "scaler_scale": float(scale),
        }
        for name, coefficient, mean, scale in zip(
            report["feature_names"], classifier.coef_[0], scaler.mean_, scaler.scale_, strict=True
        )
    ]
    matrix = np.asarray([[features[name] for name in report["feature_names"]]], dtype=float)
    probabilities = model.predict_proba(matrix)[0]
    if (
        probabilities.shape != (2,)
        or not np.isfinite(probabilities).all()
        or not ((probabilities >= 0) & (probabilities <= 1)).all()
        or not np.isclose(probabilities.sum(), 1)
    ):
        raise ValueError("Invalid binary probability output")
    durations_ms = []
    for _ in range(100):
        start = perf_counter()
        model.predict_proba(matrix)
        durations_ms.append((perf_counter() - start) * 1000)
    probability = float(probabilities[1])
    return {
        "generated_utc": datetime.now(UTC).isoformat(),
        "origin": "simulado",
        "data_source": "synthetic",
        "disclaimer": (
            "Illustrative synthetic academic inference only, not actual customer data or an "
            "observed outcome. Probabilities are not calibrated for real customers. "
            "No credit decisions, production access, retraining, final-test inference, "
            "evaluation, model selection or threshold reselection."
        ),
        "artifact": {
            "filename": artifact_path.name,
            "sha256": digest,
            "sha256_matches_report": True,
            "report_filename": report_path.name,
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "trust_caveat": (
                "Report hash checks integrity against a trusted report, not authenticity."
            ),
            "pipeline": [type(scaler).__name__, type(classifier).__name__],
            "classes": [0, 1],
            "selected_model_from_report": report["chosen"]["model"],
        },
        "feature_names": report["feature_names"],
        "coefficients": coefficients,
        "standardized_intercept": float(classifier.intercept_[0]),
        "coefficient_interpretation": (
            "For class 1 (late_payment), each coefficient is the conditional log-odds change "
            "per one fitted scaler unit, holding other features fixed; exp(coefficient) is "
            "the odds multiplier, not a probability multiplier or causal effect. Correlated "
            "and derived features limit interpretation; this is a synthetic fitted association."
        ),
        "input": {
            "source": (
                "user_supplied_mvp_features" if input_json else "APF2_new_illustrative_vector"
            ),
            "origin": "simulado",
            "actual_late_payment": None,
            "actual_label_status": "unknown_not_observed",
            "matches_predefined_case": False,
            "predefined_case_count_checked": len(cases["cases"]),
            "features": features,
        },
        "output": {
            "origin": "simulado",
            "target": "late_payment",
            "probability_class_0": float(probabilities[0]),
            "probability_class_1": probability,
            "threshold": report["chosen"]["threshold"],
            "threshold_policy": (
                "original frozen threshold; prediction = probability_class_1 >= 0.4"
            ),
            "prediction": int(probability >= report["chosen"]["threshold"]),
        },
        "latency": {
            "scope": "local_process_only",
            "clock": "time.perf_counter",
            "single_record_calls": 100,
            "warmup_calls_excluded": 1,
            "median_ms": float(np.median(durations_ms)),
            "p95_ms": float(np.percentile(durations_ms, 95, method="linear")),
            "p95_method": "numpy.percentile linear interpolation",
            "feature_preparation": (
                "Excluded: JSON reading, validation and ordered (1, 11) numpy matrix creation "
                "occur before timing. Each timed pipeline.predict_proba call includes "
                "StandardScaler.transform and LogisticRegression.predict_proba."
            ),
            "excluded": "Imports, artifact loading, warmup, file I/O, HTTP, network and database",
            "caveat": "Local Docker microbenchmark, not service latency or a production SLA.",
        },
        "runtime": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__,
            "platform": platform.platform(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-dir", type=Path, required=True, help="Trusted existing artifact dir"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New JSON path; parent must exist"
    )
    parser.add_argument(
        "--input-json", type=Path, help="Object containing exactly 11 MVP feature keys"
    )
    args = parser.parse_args()
    try:
        if args.output.resolve().is_relative_to(args.artifact_dir.resolve()):
            raise ValueError("Output must remain outside the artifact directory")
        if args.output.exists():
            raise ValueError("Output already exists; refusing to overwrite evidence")
        result = inspect_artifact(args.artifact_dir, args.input_json)
        serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
        with args.output.open("x", encoding="utf-8") as output:
            output.write(serialized)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        parser.exit(2, f"Inspection failed: {exc}\n")
    print(args.output)


if __name__ == "__main__":
    main()
