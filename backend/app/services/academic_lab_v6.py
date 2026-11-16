"""Read-only inference from a trusted, deployment-pinned V6 web bundle.

The root web manifest must be supplied by the trusted preparer on a read-only
mount. Its hashes detect corruption, not a malicious publisher or pickle.
No training runner, cohort prediction, database or business service is used.
"""

import hashlib
import io
import json
import math
import platform
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn

from app.services.academic_v6_policy import pre_model_decision

VERSION = "academic-owner-pending-v6"
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
RUNTIME = {
    "python": "3.12.14",
    "sklearn": "1.9.1",
    "numpy": "2.5.3",
    "scipy": "1.18.1",
    "joblib": "1.6.0",
}
FILES = (
    "pending_v6_report.json",
    "frozen_selection.json",
    "selected_model.joblib",
    "illustrative_input.json",
    "provenance.json",
)
CASE = {
    "id": "illustrative-v6",
    "scenario": "Ejemplo nuevo sin etiqueta",
    "requested_amount": "20.00",
}
CASES = [
    CASE,
    {
        "id": "pending-balance-v6",
        "scenario": "Ejemplo ficticio con saldo pendiente",
        "requested_amount": "20.00",
    },
    {
        "id": "no-history-v6",
        "scenario": "Ejemplo ficticio sin creditos pagados",
        "requested_amount": "20.00",
    },
]
DISCLAIMER = (
    "Datos sinteticos, solo investigacion. Probabilidad experimental sin calibracion "
    "validada para clientes reales; no constituye aprobacion de credito ni modifica "
    "scores, creditos o notificaciones. Umbral individual, no cola de revision diaria "
    "con capacidad limitada. Se aplica elegibilidad previa al modelo, no la politica "
    "de cola diaria. La decision final corresponde a revision humana."
)
SELECTION_METRIC = "OOF F2 of held-out capped review actions on known labels, beta=2"
LABELS = {
    "svm": "SVM",
    "tree": "Arbol de decision",
    "most_frequent": "Dummy mayoritario",
    "constant_1": "Dummy siempre positivo",
}


def runtime_versions():
    return {
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
    }


def require(condition):
    if not condition:
        raise ValueError("Invalid academic V6 bundle")


def number(value, low=0, high=1):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high)
    return value


def count(value):
    require(type(value) is int and value >= 0)
    return value


def text(value):
    require(isinstance(value, str) and bool(value.strip()))
    return value


def json_object(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("Nonfinite JSON")

    result = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)
    require(isinstance(result, dict))
    return result


def validate_features(data):
    features = data.get("features", data)
    require(isinstance(features, dict) and set(features) == set(FEATURE_NAMES))
    require("features" not in data or set(data) == {"features"})
    for name, value in features.items():
        if value is None:
            continue
        number(value, high=float("inf"))
        if name in FEATURE_NAMES[:5] + ["tenure_days"]:
            require(int(value) == value)
        if name in ("utilization", "requested_ratio", "punctuality_rate", "overdue_rate"):
            require(value <= 1 and (name != "requested_ratio" or value > 0))
    if features["paid_credits"] is not None and features["paid_late"] is not None:
        require(features["paid_late"] <= features["paid_credits"])
    return {name: features[name] for name in FEATURE_NAMES}


def metrics(value, policy=False):
    result = {}
    for name in (
        "accuracy", "balanced_accuracy", "precision", "recall", "f1", "f2", "roc_auc", "brier"
    ):
        # Frozen policy actions have no probability/calibration metrics.
        item = value.get(name) if policy else value[name]
        require(item is not None or name == "roc_auc"
                or policy and name in ("balanced_accuracy", "brier"))
        result[name] = None if item is None else number(item)
    matrix = value["confusion_matrix"]
    require(isinstance(matrix, list) and len(matrix) == 2)
    require(all(isinstance(row, list) and len(row) == 2 for row in matrix))
    result["confusion_matrix"] = [[count(item) for item in row] for row in matrix]
    if not policy and result["roc_auc"] is None:
        require(any(sum(row) == 0 for row in result["confusion_matrix"]))
    return result


def load_bundle(directory):
    root = Path(directory)
    manifest = json_object((root / "web_manifest.json").read_bytes())
    require(set(manifest) == {"version", "files"} and manifest["version"] == VERSION)
    require(isinstance(manifest["files"], dict) and set(manifest["files"]) == set(FILES))
    contents = tuple((root / name).read_bytes() for name in FILES)
    for name, data in zip(FILES, contents, strict=True):
        manifest_hash = manifest["files"][name]
        require(isinstance(manifest_hash, str) and len(manifest_hash) == 64)
        require(hashlib.sha256(data).hexdigest() == manifest_hash)
    # Recheck disk hashes even on cache hits; deserialize only the verified bytes.
    require(runtime_versions() == RUNTIME)
    return validated_bundle(contents)


@lru_cache(maxsize=1)
def validated_bundle(contents):
    report, frozen, model_bytes, input_data, provenance = (
        data if name.endswith("joblib") else json_object(data)
        for name, data in zip(FILES, contents, strict=True)
    )
    features = validate_features(input_data)
    require(report["version"] == frozen["version"] == VERSION)
    require(report["origen"] == "simulado")
    require(report["research_only"] is True and frozen["research_only"] is True)
    require(report["business_approval"] is False)
    require(report["feature_names"] == frozen["feature_names"] == FEATURE_NAMES)
    require({key: provenance["runtime"].get(key) for key in RUNTIME} == RUNTIME)
    require(report["selection"] == frozen and report["provenance"] == provenance)
    require(
        report["artifact_sha256"]["selected_model.joblib"]
        == hashlib.sha256(model_bytes).hexdigest()
    )
    winner = frozen["global_winner"]
    family = winner["family"]
    require(family in ("tree", "svm") and family == winner["params"]["family"])
    threshold = number(winner["threshold"])
    require(number(report["models"][family]["threshold"]) == threshold)
    historical = "revision_id" not in report
    if historical:
        require("revision_id" not in frozen and "revision_id" not in provenance)
        require(family == "tree" and threshold == 0.2)
        revision_id = "v6-historical"
        display_name = text(report["display_name"]) if "display_name" in report else "V6 historico"
    else:
        revision_id, display_name = text(report["revision_id"]), text(report["display_name"])
        require(revision_id == frozen["revision_id"] == provenance["revision_id"] == "v6-final-r1")
        require(display_name == frozen["display_name"] == provenance["display_name"] == "V6 Final")
        require(report["artifact_sha256"][family + ".joblib"]
                == report["artifact_sha256"]["selected_model.joblib"])
    development, final = report["development"], report["final"]
    routing = None
    if not historical:
        routing = {}
        for name, cohort in (("development", development), ("final", final)):
            values = {key: count(cohort["routing"][key]) for key in (
                "blocked_pending_balance", "requires_owner_review", "model_eligible",
                "simulator_refused_model_eligible",
            )}
            values["study_attempts"] = count(cohort["study_attempts"])
            require(values["study_attempts"] == sum(values[key] for key in (
                "blocked_pending_balance", "requires_owner_review", "model_eligible")))
            require(values["model_eligible"] - values["simulator_refused_model_eligible"]
                    == count(cohort["study_rows"]))
            require(count(cohort["known_rows"]) + count(cohort["unknown_rows"])
                    == cohort["study_rows"])
            routing[name] = values
    comparison = []
    for family, label in LABELS.items():
        model = report["models"][family]
        policy = model["review_policy"]["final"]
        require(type(policy["capacity_respected"]) is bool)
        comparison.append({
            "family": family,
            "label": label,
            "raw": metrics(model["final"]),
            "policy": {
                "metrics": metrics(policy["metrics"], policy=True),
                **{key: count(policy[key]) for key in (
                    "reviews", "reviews_known", "reviews_unknown", "daily_max"
                )},
                "capacity_respected": policy["capacity_respected"],
            },
        })
    anchors = provenance["source_anchors"]
    limitations = report["limits"]
    require(isinstance(limitations, list) and bool(limitations))
    summary = {
        "version": VERSION,
        "revision_id": revision_id,
        "display_name": display_name,
        "data_source": "synthetic",
        "research_only": True,
        "business_approval": False,
        "selected_model": winner["family"],
        "training_scope": "eligible_known_only" if not historical else "historical_granted_known",
        "routing": routing,
        "threshold": threshold,
        "development_rows": count(development["study_rows"]),
        "development_unknown": count(development["unknown_rows"]),
        "development_clients": sum(count(audit["clients"]) for audit in development["audits"]),
        "final_labeled_rows": count(final["known_rows"]),
        "final_unknown": count(count(final["study_rows"]) - final["known_rows"]),
        "final_clients": (count(final["audit"]["clients"]) if historical
                          else sum(count(audit["clients"]) for audit in final["audits"])),
        "selection": {
            "metric": text(SELECTION_METRIC),
            "oof_f2": number(winner["review_policy"]["metrics"]["f2"]),
        },
        "comparison": comparison,
        "source": {
            "evaluable": count(anchors["evaluable"]),
            "late": count(anchors["late"]),
            "partial_annotations": count(anchors["partial_payment_annotations"]),
            "partial_denominator": count(anchors["partial_payment_denominator"]),
            "quality": text(anchors["source_quality"]),
        },
        "limitations": [text(item) for item in limitations],
        "disclaimer": DISCLAIMER,
    }
    return summary, features, model_bytes


@lru_cache(maxsize=1)
def load_model(model_bytes):
    model = joblib.load(io.BytesIO(model_bytes))
    classes = np.asarray(model.classes_)
    require(classes.shape == (2,) and classes.dtype.kind in "iuf")
    require(classes.tolist() == [0, 1])
    require(model.n_features_in_ == len(FEATURE_NAMES))
    if hasattr(model, "feature_names_in_"):
        require(list(model.feature_names_in_) == FEATURE_NAMES)
    require(callable(model.predict_proba))
    return model


def evaluate(bundle, case_id="illustrative-v6"):
    summary, features, model_bytes = bundle
    case = next((item for item in CASES if item["id"] == case_id), None)
    require(case is not None)
    features = dict(features)
    if case_id == "pending-balance-v6":
        features.update(pending_current=1, outstanding=20, utilization=0.25)
    elif case_id == "no-history-v6":
        features.update(
            completed_sales=0, paid_credits=0, paid_late=0, punctuality_rate=0,
            tenure_days=0, pending_overdue=0, pending_current=0, outstanding=0,
            utilization=0, overdue_rate=0,
        )
    features = validate_features(features)
    decision = pre_model_decision(features)
    result = {
        "case_id": case["id"],
        "scenario": case["scenario"],
        "data_source": "synthetic",
        "version": VERSION,
        "research_only": True,
        "business_approval": False,
        "estimated_late_probability": None,
        "threshold": None,
        "predicted_late_payment": None,
        "actual_late_payment": None,
        "features": features,
        "review_policy_applied": False,
        "disclaimer": DISCLAIMER,
        "model_called": False,
    }
    if decision is not None:
        return {**result, **decision}
    model = load_model(model_bytes)
    vector = np.asarray([
        [np.nan if features[name] is None else float(features[name]) for name in FEATURE_NAMES]
    ])
    positive_index = list(model.classes_).index(1)
    probabilities = np.asarray(model.predict_proba(vector))
    require(probabilities.shape == (1, 2))
    require(
        np.isfinite(probabilities).all() and ((0 <= probabilities) & (probabilities <= 1)).all()
    )
    probability = float(probabilities[0, positive_index])
    return {
        **result,
        "estimated_late_probability": probability,
        "threshold": summary["threshold"],
        "predicted_late_payment": int(probability >= summary["threshold"]),
        "decision": ("model_review_candidate" if probability >= summary["threshold"]
                     else "below_review_threshold"),
        "reason": (
            "Estimacion experimental para revision humana, no aprobacion de credito. "
            "Se aplica el umbral individual, no la capacidad de la cola diaria."
        ),
        "requires_manual_review": True,
        "model_called": True,
    }
