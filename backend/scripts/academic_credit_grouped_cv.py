"""Frozen APF3 offline research runner. Importing this module never runs an experiment.

Run from the source checkout with --source LEDGER --protocol JSON --output-dir NEW.
The predict function/CLI loads an existing artifact without training or generating data.
Only synthetic, features and outcomes from app.ml are needed by the experiment.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import itertools
import json
import platform
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, export_text

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

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
ILLUSTRATIVE_VECTOR = [3, 2, 1, 0, 0, 0, 0, 0.25, 45, 0.5, 0]
BASELINES = ("most_frequent", "constant_1")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    """Exclusive creation protects persisted evidence, including inference outputs."""
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, indent=2, allow_nan=False)
        file.write("\n")


def prepare_output(output: Path) -> Path:
    output = output.resolve()
    if output.is_relative_to((BACKEND / "app").resolve()):
        raise ValueError("Academic outputs must remain outside production app")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must be new or empty; never reuse evidence")
    output.mkdir(parents=True, exist_ok=True)
    return output


def validate_protocol(protocol: dict) -> None:
    """Reject unsupported protocols instead of silently substituting experiment defaults."""
    expected = {
        "version": "academic-grouped-cv-v3",
        "target": "late_payment",
        "development_splits": ["train", "validation"],
        "cv": {
            "type": "StratifiedGroupKFold",
            "folds": 5,
            "shuffle": True,
            "seed": 20261112,
            "group": "client_id",
        },
        "preprocessing": ["SimpleImputer(strategy=median)", "StandardScaler"],
        "tree": {
            "max_depth": [2, 3, 4],
            "min_samples_leaf": [8, 16],
            "class_weight": [None, "balanced"],
            "random_state": 42,
        },
        "svm": {
            "kernel": "linear",
            "C": [0.1, 1.0, 10.0],
            "class_weight": [None, "balanced"],
            "probability": False,
            "random_state": 42,
        },
        "svm_calibration": {
            "method": "sigmoid",
            "folds": 3,
            "group": "client_id",
            "ensemble": False,
            "seed": 20261114,
            "scope": "Only within the training portion of each outer fold; "
            "preprocessing inside each calibrated estimator",
        },
        "thresholds": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        "baselines": [
            "DummyClassifier(strategy=most_frequent)",
            "DummyClassifier(strategy=constant,constant=1)",
        ],
        "final_cohort": {
            "generator": "Unchanged existing transaction simulator",
            "seed": 20261117,
            "clients": 120,
            "id_prefix": "CV3",
            "generation": "Only after frozen_selection.json exists",
            "policy": "One final evaluation of all frozen models on same cohort; "
            "no post-result tuning or seed changes",
        },
    }
    for key, value in expected.items():
        if protocol.get(key) != value:
            raise ValueError(f"Unsupported frozen protocol field: {key}")
    selection = protocol["selection"]
    if (
        selection["metric"] != "F2"
        or selection["beta"] != 2
        or selection["minimum_precision"] != 0.5
        or selection["tie_breakers"]
        != [
            "recall",
            "f1",
            "precision",
            "Earlier candidate in declared grid",
            "Threshold nearest 0.5",
        ]
    ):
        raise ValueError("Unsupported frozen selection policy")


def matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(
        [
            [np.nan if row[name] is None else float(row[name]) for name in FEATURE_NAMES]
            for row in rows
        ],
        dtype=float,
    )
    y = np.asarray([row["late_payment"] for row in rows], dtype=int)
    if x.shape != (len(rows), 11) or not len(rows) or np.isinf(x).any():
        raise ValueError("Expected nonempty eleven-feature matrix without infinities")
    if not set(y.tolist()) <= {0, 1}:
        raise ValueError("Expected binary resolved labels")
    return x, y


def load_development(source: Path, protocol: dict) -> tuple[dict, list[dict]]:
    data = source.read_bytes()
    if sha256(data) != protocol["development_source_sha256"]:
        raise ValueError("Development source SHA256 does not match frozen protocol")
    ledger = json.loads(data)
    memberships: dict[str, str] = {}
    for row in ledger["rows"]:
        previous = memberships.setdefault(row["client_id"], row["split"])
        if previous != row["split"]:
            raise ValueError("Source client crosses original train/validation/test splits")
    rows = [
        row
        for row in ledger["rows"]
        if row["split"] in protocol["development_splits"] and row["late_payment"] is not None
    ]
    if len({row["loan_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate development loan IDs")
    matrix(rows)
    return ledger, rows


def grouped_splits(x, y, groups, folds: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    groups = np.asarray(groups)
    splits = list(
        StratifiedGroupKFold(
            n_splits=folds,
            shuffle=True,
            random_state=seed,
        ).split(x, y, groups)
    )
    coverage = np.zeros(len(y), dtype=int)
    for train, validation in splits:
        if set(groups[train]) & set(groups[validation]):
            raise ValueError("Client leakage in grouped folds")
        if len(np.unique(y[train])) != 2 or len(np.unique(y[validation])) != 2:
            raise ValueError("Both labels required in each fold; do not change frozen seed")
        coverage[validation] += 1
    if not np.all(coverage == 1):
        raise ValueError("Every OOF row must be predicted exactly once")
    return splits


def fold_audit(splits, groups, parent_indices=None) -> list[dict]:
    groups = np.asarray(groups)
    parent = np.arange(len(groups)) if parent_indices is None else np.asarray(parent_indices)
    return [
        {
            "fold": number,
            "train_indices": parent[train].tolist(),
            "validation_indices": parent[validation].tolist(),
            "train_client_ids": sorted(set(groups[train].tolist())),
            "validation_client_ids": sorted(set(groups[validation].tolist())),
            "client_disjoint": not bool(set(groups[train]) & set(groups[validation])),
        }
        for number, (train, validation) in enumerate(splits)
    ]


def candidate_grid(protocol: dict) -> list[dict]:
    tree, svm = protocol["tree"], protocol["svm"]
    candidates = [
        {
            "family": "tree",
            "max_depth": depth,
            "min_samples_leaf": leaf,
            "class_weight": weight,
            "random_state": tree["random_state"],
        }
        for depth, leaf, weight in itertools.product(
            tree["max_depth"], tree["min_samples_leaf"], tree["class_weight"]
        )
    ]
    candidates.extend(
        {
            "family": "svm",
            "C": c,
            "class_weight": weight,
            "kernel": svm["kernel"],
            "probability": svm["probability"],
            "random_state": svm["random_state"],
        }
        for c, weight in itertools.product(svm["C"], svm["class_weight"])
    )
    return candidates


def build_model(params: dict, x, y, groups):
    """Build and fit afresh; calibration indices are local to this training matrix only."""
    options = {key: value for key, value in params.items() if key != "family"}
    family = params["family"]
    if family == "tree":
        classifier = DecisionTreeClassifier(**options)
    elif family == "svm":
        if options.get("probability") is not False:
            raise ValueError("SVM must use explicit group-disjoint sigmoid calibration")
        classifier = SVC(**options)
    elif family == "most_frequent":
        classifier = DummyClassifier(strategy="most_frequent")
    elif family == "constant_1":
        classifier = DummyClassifier(strategy="constant", constant=1)
    else:
        raise ValueError(f"Unknown family: {family}")
    if np.isnan(np.asarray(x)).all(axis=0).any():
        raise ValueError("All-missing training feature would change the eleven-feature schema")
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    )
    if family == "svm":
        splits = grouped_splits(x, y, groups, folds=3, seed=20261114)
        model = CalibratedClassifierCV(
            estimator=model,
            cv=splits,
            method="sigmoid",
            ensemble=False,
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(x, y)
    except ConvergenceWarning as error:
        raise RuntimeError(
            "Frozen CV failed convergence; no automatic retuning/reseeding"
        ) from error
    return model


def positive_scores(model, x) -> np.ndarray:
    return np.asarray(model.predict_proba(x)[:, list(model.classes_).index(1)], dtype=float)


def metrics(y, scores, threshold: float) -> dict:
    scores = np.asarray(scores, dtype=float)
    predicted = (scores >= threshold).astype(int)
    return {
        "n": len(y),
        "f2": float(fbeta_score(y, predicted, beta=2, zero_division=0)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "accuracy": float(accuracy_score(y, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
        "roc_auc": float(roc_auc_score(y, scores)) if len(np.unique(y)) == 2 else None,
        "brier": float(brier_score_loss(y, scores)),
        "confusion_matrix": confusion_matrix(y, predicted, labels=[0, 1]).tolist(),
        "confusion_labels": [0, 1],
    }


def oof_predict(params: dict, x, y, groups, splits) -> tuple[np.ndarray, np.ndarray]:
    scores, coverage = np.full(len(y), np.nan), np.zeros(len(y), dtype=int)
    for train, validation in splits:
        model = build_model(params, x[train], y[train], groups[train])
        scores[validation] = positive_scores(model, x[validation])
        coverage[validation] += 1
    if not np.all(coverage == 1) or not np.isfinite(scores).all():
        raise ValueError("OOF predictions must be finite and cover every row exactly once")
    return scores, coverage


def select_candidate(entries: list[dict], minimum_precision: float = 0.5) -> dict:
    eligible = [entry for entry in entries if entry["metrics"]["precision"] >= minimum_precision]

    def rank(entry):
        value = entry["metrics"]
        return (
            value["f2"],
            value["recall"],
            value["f1"],
            value["precision"],
            -entry["candidate_index"],
            -round(abs(entry["threshold"] - 0.5), 12),
        )

    chosen = copy.deepcopy(max(eligible or entries, key=rank))
    chosen["feasible"] = bool(eligible)
    chosen["constraint_failure"] = not bool(eligible)
    chosen["research_only"] = True
    return chosen


def rename_final(ledger: dict, source_client_ids: set[str]) -> dict:
    clients = {
        client["client_id"]: f"CV3-C{index:04d}"
        for index, client in enumerate(ledger["clients"], 1)
    }
    loans = {loan["loan_id"]: f"CV3-L{index:05d}" for index, loan in enumerate(ledger["loans"], 1)}
    if set(clients.values()) & source_client_ids:
        raise ValueError("Final clients overlap source clients")
    for collection in ("clients", "loans", "sales", "rows"):
        for row in ledger[collection]:
            row["client_id"] = clients[row["client_id"]]
            if "loan_id" in row:
                row["loan_id"] = loans[row["loan_id"]]
            row["split"] = "final_test"
            row["origen"] = "simulado"
    ledger["origen"] = "simulado"
    return ledger


def evaluate_final_once(model, rows: list[dict], x, y, threshold: float) -> dict:
    """The only final-matrix prediction call; all exports reuse its cached scores."""
    scores = positive_scores(model, x)
    predictions, errors = [], []
    for row, score in zip(rows, scores, strict=True):
        case = {
            "origen": "simulado",
            "client_id": row["client_id"],
            "loan_id": row["loan_id"],
            "scenario": row["scenario"],
            "features": {name: row[name] for name in FEATURE_NAMES},
            "probability": float(score),
            "actual": row["late_payment"],
            "predicted": int(score >= threshold),
            "threshold": threshold,
        }
        predictions.append(case)
        if case["actual"] != case["predicted"]:
            errors.append({**case, "error_type": "FP" if case["predicted"] else "FN"})
    return {
        "metrics": metrics(y, scores, threshold),
        "predictions": predictions,
        "error_count": len(errors),
        "error_cases": errors[:10],
        "error_cases_note": "First up to ten errors, not selected for tuning; "
        "fewer than three only if fewer than three errors exist",
    }


def interpretation(model, family: str) -> dict:
    if family == "tree":
        raw_tree = copy.deepcopy(model.named_steps["classifier"])
        scaler = model.named_steps["scaler"]
        for node, feature in enumerate(raw_tree.tree_.feature):
            if feature >= 0:
                raw_tree.tree_.threshold[node] = (
                    raw_tree.tree_.threshold[node] * scaler.scale_[feature] + scaler.mean_[feature]
                )
        return {
            "raw_unit_rules": export_text(raw_tree, feature_names=FEATURE_NAMES, decimals=6),
            "caveat": "Rules use raw units after training-median imputation; "
            "saved pipeline is unchanged. Rules are not causal.",
        }
    if family == "svm":
        pipeline = model.calibrated_classifiers_[0].estimator
        classifier = pipeline.named_steps["classifier"]
        return {
            "standardized_coefficients": dict(
                zip(FEATURE_NAMES, classifier.coef_[0].tolist(), strict=True)
            ),
            "intercept": float(classifier.intercept_[0]),
            "caveat": "Coefficients describe standardized linear SVM margin, "
            "not calibrated probabilities, causal effects or business importance.",
        }
    return {"caveat": "Dummy reference, not a learned risk model"}


def predict(artifact_dir: Path, input_data: dict) -> dict:
    """Inference only. Load only trusted joblib artifacts; never unpickle user uploads."""
    frozen_bytes = (artifact_dir / "frozen_selection.json").read_bytes()
    frozen = json.loads(frozen_bytes)
    if frozen["feature_names"] != FEATURE_NAMES:
        raise ValueError("Artifact feature order does not match eleven-feature schema")
    features = input_data.get("features", input_data)
    if set(features) != set(FEATURE_NAMES):
        raise ValueError("Input must contain exactly the eleven named features, no known label")
    for name, value in features.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite nonnegative number or null")
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite nonnegative number or null")
        if name in FEATURE_NAMES[:5] + ["tenure_days"] and int(value) != value:
            raise ValueError(f"{name} must be integral")
        if name in ("utilization", "requested_ratio", "punctuality_rate", "overdue_rate"):
            if value > 1 or (name == "requested_ratio" and value == 0):
                raise ValueError(f"{name} is outside the academic input range")
    paid, late = features["paid_credits"], features["paid_late"]
    if paid is not None and late is not None and late > paid:
        raise ValueError("paid_late cannot exceed paid_credits")
    vector = [
        [np.nan if features[name] is None else float(features[name]) for name in FEATURE_NAMES]
    ]
    if np.isinf(vector).any():
        raise ValueError("Infinite input features are not supported")
    manifest = json.loads((artifact_dir / "artifact_manifest.json").read_text())
    artifact = artifact_dir / "selected_model.joblib"
    artifact_bytes = artifact.read_bytes()
    if sha256(artifact_bytes) != manifest["selected_model.joblib"]:
        raise ValueError("Selected artifact SHA256 mismatch; refusing deserialization")
    if sha256(frozen_bytes) != manifest["frozen_selection.json"]:
        raise ValueError("Frozen selection SHA256 mismatch")
    model = joblib.load(io.BytesIO(artifact_bytes))
    score = float(positive_scores(model, vector)[0])
    threshold = frozen["global_winner"]["threshold"]
    return {
        "origen": "simulado",
        "illustrative_only": True,
        "known_label": None,
        "family": frozen["global_winner"]["family"],
        "feature_names": FEATURE_NAMES,
        "features": features,
        "probability": score,
        "threshold": threshold,
        "predicted": int(score >= threshold),
        "research_only": True,
    }


def baseline_comparison(model_metrics: dict, selected: str, minimum_precision: float) -> dict:
    comparison = {}
    for split in ("train", "oof", "final"):
        chosen = model_metrics[selected][split]
        references = {
            name: {
                "f2": model_metrics[name][split]["f2"],
                "feasible": model_metrics[name][split]["precision"] >= minimum_precision,
                "selected_f2_strictly_higher": chosen["f2"] > model_metrics[name][split]["f2"],
            }
            for name in BASELINES
        }
        comparison[split] = {
            "baselines": references,
            "selected_feasible": chosen["precision"] >= minimum_precision,
            "selected_superior_to_both": chosen["precision"] >= minimum_precision
            and all(
                item["feasible"] and item["selected_f2_strictly_higher"]
                for item in references.values()
            ),
            "caveat": "Descriptive F2 comparison only, not statistical or business superiority; "
            "no superiority claim if a baseline is ineligible or not beaten.",
        }
    return comparison


def run(source: Path, protocol_path: Path, output: Path) -> dict:
    # App imports remain out of inference mode and do not import routes/training/services.
    from app.ml.features import FEATURE_NAMES as app_feature_names
    from app.ml.synthetic import generate_academic_dataset, validate_academic_dataset

    if FEATURE_NAMES != app_feature_names:
        raise ValueError("Feature order must exactly match app.ml.features.FEATURE_NAMES")
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    validate_protocol(protocol)
    original, rows = load_development(source, protocol)
    output = prepare_output(output)
    with (output / "protocol.json").open("xb") as file:
        file.write(protocol_bytes)
    code_paths = {
        "runner": Path(__file__).resolve(),
        **{
            name: BACKEND / "app" / "ml" / f"{name}.py"
            for name in ("synthetic", "features", "outcomes")
        },
    }
    provenance = {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "protocol_sha256": sha256(protocol_bytes),
        "source_sha256": sha256(source.read_bytes()),
        "development_sha256": sha256(json.dumps(rows, sort_keys=True).encode()),
        "code_sha256": {name: sha256(path.read_bytes()) for name, path in code_paths.items()},
        "runtime": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__,
            "scipy": scipy.__version__,
        },
        "feature_names": FEATURE_NAMES,
        "development_rows": len(rows),
        "development_clients": len({row["client_id"] for row in rows}),
        "excluded_rows": len(original["rows"]) - len(rows),
        "source_path": str(source.resolve()),
        "policy": "Original train + validation only, resolved labels; old test excluded",
    }
    write_json(output / "provenance.json", provenance)
    x, y = matrix(rows)
    groups = np.asarray([row["client_id"] for row in rows])
    cv = protocol["cv"]
    splits = grouped_splits(x, y, groups, cv["folds"], cv["seed"])
    calibration_audit = []
    for fold, (train, _) in enumerate(splits):
        inner = grouped_splits(x[train], y[train], groups[train], 3, 20261114)
        calibration_audit.append(
            {"outer_fold": fold, "folds": fold_audit(inner, groups[train], train)}
        )
    full_inner = grouped_splits(x, y, groups, 3, 20261114)
    write_json(
        output / "fold_audit.json",
        {
            "index_space": "development_rows.json row order; calibration indices mapped to it",
            "outer": fold_audit(splits, groups),
            "svm_outer_training_calibration": calibration_audit,
            "svm_full_development_calibration": fold_audit(full_inner, groups),
        },
    )
    write_json(output / "development_rows.json", rows)
    search, flat_entries, scores_by_candidate = [], [], {}
    for index, params in enumerate(candidate_grid(protocol)):
        scores, coverage = oof_predict(params, x, y, groups, splits)
        scores_by_candidate[index] = scores
        entries = [
            {
                "family": params["family"],
                "candidate_index": index,
                "params": params,
                "threshold": threshold,
                "metrics": metrics(y, scores, threshold),
            }
            for threshold in protocol["thresholds"]
        ]
        flat_entries.extend(entries)
        search.append(
            {
                "candidate_index": index,
                "params": params,
                "threshold_results": entries,
                "oof_probabilities": scores.tolist(),
                "oof_prediction_counts": coverage.tolist(),
            }
        )
    baseline_oof = {}
    for name in BASELINES:
        scores, coverage = oof_predict({"family": name}, x, y, groups, splits)
        baseline_oof[name] = {
            "params": {"family": name},
            "threshold": 0.5,
            "metrics": metrics(y, scores, 0.5),
            "oof_probabilities": scores.tolist(),
            "oof_prediction_counts": coverage.tolist(),
        }
    # Search evidence must exist before the frozen decision file, not just in memory.
    write_json(output / "cv_search.json", {"candidates": search, "baselines": baseline_oof})
    minimum_precision = protocol["selection"]["minimum_precision"]
    families = {
        name: select_candidate(
            [entry for entry in flat_entries if entry["family"] == name],
            minimum_precision,
        )
        for name in ("tree", "svm")
    }
    winner = select_candidate(list(families.values()), minimum_precision)
    frozen = {
        "frozen_utc": datetime.now(UTC).isoformat(),
        "feature_names": FEATURE_NAMES,
        "protocol_sha256": provenance["protocol_sha256"],
        "source_sha256": provenance["source_sha256"],
        "development_sha256": provenance["development_sha256"],
        "families": families,
        "global_winner": winner,
        "baselines": {
            name: {
                "params": item["params"],
                "threshold": item["threshold"],
                "metrics": item["metrics"],
                "feasible": item["metrics"]["precision"] >= minimum_precision,
            }
            for name, item in baseline_oof.items()
        },
        "constraint_failure": winner["constraint_failure"],
        "research_only": True,
        "oof_caveat": protocol["selection"]["oof_limit"],
    }
    write_json(output / "frozen_selection.json", frozen)
    choices = {**families, **frozen["baselines"]}
    models, model_reports = {}, {}
    for name, choice in choices.items():
        model = build_model(choice["params"], x, y, groups)
        models[name] = model
        joblib.dump(model, output / f"{name}.joblib")
        model_reports[name] = {
            "params": choice["params"],
            "threshold": choice["threshold"],
            "oof_feasible": choice["metrics"]["precision"] >= minimum_precision,
            "train": metrics(y, positive_scores(model, x), choice["threshold"]),
            "oof": choice["metrics"],
            "artifact": f"{name}.joblib",
            "interpretation": interpretation(model, name),
        }
    joblib.dump(models[winner["family"]], output / "selected_model.joblib")
    write_json(
        output / "artifact_manifest.json",
        {
            filename: sha256((output / filename).read_bytes())
            for filename in ["selected_model.joblib", "frozen_selection.json"]
        },
    )

    # No generator access before persisted selection, and no training after this boundary.
    final_spec = protocol["final_cohort"]
    final_ledger = generate_academic_dataset(final_spec["clients"], final_spec["seed"])
    final_ledger = rename_final(
        final_ledger,
        {row["client_id"] for collection in ("clients", "rows") for row in original[collection]},
    )
    final_checks = validate_academic_dataset(final_ledger)
    if not all(
        row["split"] == "final_test" and row["client_id"].startswith("CV3")
        for collection in ("clients", "loans", "sales", "rows")
        for row in final_ledger[collection]
    ):
        raise ValueError("Final cohort IDs/splits are inconsistent")
    final_rows = [row for row in final_ledger["rows"] if row["late_payment"] is not None]
    x_final, y_final = matrix(final_rows)
    write_json(output / "final_transactions.json", final_ledger)
    final_results = {}
    for name, model in models.items():
        result = evaluate_final_once(
            model,
            final_rows,
            x_final,
            y_final,
            choices[name]["threshold"],
        )
        final_results[name] = result
        model_reports[name]["final"] = result["metrics"]
        model_reports[name]["error_count"] = result["error_count"]
        model_reports[name]["error_cases"] = result["error_cases"]
        model_reports[name]["error_cases_note"] = result["error_cases_note"]
    write_json(output / "final_predictions.json", final_results)
    with (output / "final_predictions.csv").open("x", newline="", encoding="utf-8") as file:
        fields = [
            "model",
            "origen",
            "client_id",
            "loan_id",
            "scenario",
            "actual",
            "predicted",
            "probability",
            "threshold",
            *FEATURE_NAMES,
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for name, result in final_results.items():
            for case in result["predictions"]:
                writer.writerow(
                    {
                        "model": name,
                        **{key: value for key, value in case.items() if key != "features"},
                        **case["features"],
                    }
                )
    illustrative = dict(zip(FEATURE_NAMES, ILLUSTRATIVE_VECTOR, strict=True))
    for row in itertools.chain(original["rows"], final_ledger["rows"]):
        vector = [row[name] for name in FEATURE_NAMES]
        if vector == ILLUSTRATIVE_VECTOR:
            raise ValueError("Prespecified illustrative input duplicates an existing row")
    write_json(output / "illustrative_input.json", {"features": illustrative})
    # Reload the serialized selected pipeline; do not run any final row through it again.
    example = predict(output, {"features": illustrative})
    write_json(output / "illustrative_prediction.json", example)
    artifacts = [f"{name}.joblib" for name in choices] + ["selected_model.joblib"]
    report = {
        "version": protocol["version"],
        "generated_utc": datetime.now(UTC).isoformat(),
        "origen": "simulado",
        "research_only": True,
        "target": protocol["target"],
        "feature_names": FEATURE_NAMES,
        "provenance": provenance,
        "selection": frozen,
        "development": {
            "rows": len(rows),
            "clients": len(set(groups)),
            "original_split_counts": {
                split: sum(row["split"] == split for row in rows)
                for split in protocol["development_splits"]
            },
        },
        "final_cohort": {
            "seed": final_spec["seed"],
            "clients": len(final_ledger["clients"]),
            "labeled_rows": len(final_rows),
            "checks": final_checks,
            "source_clients_disjoint": True,
            "evaluation_calls_per_model": {name: 1 for name in choices},
            "policy": final_spec["policy"],
        },
        "models": model_reports,
        "baseline_comparison": baseline_comparison(
            model_reports, winner["family"], minimum_precision
        ),
        "illustrative_inference": example,
        "artifact_sha256": {name: sha256((output / name).read_bytes()) for name in artifacts},
        "limitations": protocol["limitations"]
        + [
            protocol["selection"]["oof_limit"],
            "Precision floor and F2 are technical assumptions, not business readiness",
        ],
    }
    write_json(output / "grouped_cv_report.json", report)
    return report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Source transaction ledger JSON, not directory")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--predict-artifact-dir", type=Path)
    parser.add_argument("--input-json", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)
    if args.predict_artifact_dir is not None:
        if (
            args.input_json is None
            or args.output_json is None
            or any(value is not None for value in (args.source, args.protocol, args.output_dir))
        ):
            parser.error("Inference requires --input-json/--output-json and no experiment flags")
        if args.output_json.resolve().is_relative_to((BACKEND / "app").resolve()):
            parser.error("Inference output must remain outside production app")
        if args.output_json.exists():
            parser.error("Inference output must be a new file")
        result = predict(args.predict_artifact_dir, json.loads(args.input_json.read_text()))
        write_json(args.output_json, result)
    else:
        if (
            any(value is None for value in (args.source, args.protocol, args.output_dir))
            or args.input_json is not None
            or args.output_json is not None
        ):
            parser.error("Experiment requires --source/--protocol/--output-dir only")
        result = run(args.source, args.protocol, args.output_dir)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
