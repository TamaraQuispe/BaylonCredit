"""Frozen owner-aligned synthetic research; importing never generates or fits.

Experiment: --calibration JSON --protocol JSON --output-dir NEW.
Inference: --predict-artifact-dir TRUSTED_DIR --input-json JSON --output-json NEW.
Joblib is executable: hashes detect corruption, not an untrusted artifact publisher.
"""

from __future__ import annotations

import argparse
import copy
import csv
import inspect
import io
import json
import platform
import sys
import warnings
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts.academic_credit_grouped_cv import (  # noqa: E402
    FEATURE_NAMES,
    candidate_grid,
    fold_audit,
    interpretation,
    matrix,
    metrics,
    positive_scores,
    prepare_output,
    sha256,
    write_json,
)

PROTOCOL_SHA256 = "b9a6c49c2e2cb3b0e036fb9e5ce37f69421c31e6d98ccb096b7ba37b8760345c"
CALIBRATION_SHA256 = "81f858bc8827c88e41352745f65345a72d2b9d06361046bc86d3f07540806064"
BASELINES = ("most_frequent", "constant_1")
FAMILIES = ("tree", "svm")


def validate_sources(calibration_bytes: bytes, protocol_bytes: bytes) -> None:
    if sha256(calibration_bytes) != CALIBRATION_SHA256:
        raise ValueError(
            "Only frozen current Rildo aggregate anchors are allowed; old form excluded"
        )
    if sha256(protocol_bytes) != PROTOCOL_SHA256:
        raise ValueError("Unsupported frozen aligned-v4 protocol SHA256")


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode())


def grouped_splits(x, y, groups, seed: int) -> list:
    """Fallback is based only on class adequacy, never fitted scores."""
    groups = np.asarray(groups)
    for count in (3, 2):
        if len(np.unique(groups)) < count or min(np.bincount(y, minlength=2)) < count:
            continue
        splits = list(
            StratifiedGroupKFold(n_splits=count, shuffle=True, random_state=seed).split(
                x, y, groups
            )
        )
        coverage = np.zeros(len(y), dtype=int)
        adequate = True
        for train, valid in splits:
            if set(groups[train]) & set(groups[valid]):
                raise ValueError("Client leakage in grouped folds")
            adequate &= len(np.unique(y[train])) == len(np.unique(y[valid])) == 2
            coverage[valid] += 1
        if adequate and np.all(coverage == 1):
            return splits
    raise ValueError("Neither 3 nor 2 grouped folds has both classes in every subset")


def fit_model(params: dict, x, y, groups, inner_splits=None):
    options = {key: value for key, value in params.items() if key != "family"}
    family = params["family"]
    if family == "tree":
        classifier = DecisionTreeClassifier(**options)
    elif family == "svm":
        if options.get("probability") is not False or options.get("kernel") != "linear":
            raise ValueError("SVM requires linear margin and grouped explicit calibration")
        classifier = SVC(**options)
    elif family in BASELINES:
        classifier = (
            DummyClassifier(strategy="most_frequent")
            if family == "most_frequent"
            else DummyClassifier(strategy="constant", constant=1)
        )
    else:
        raise ValueError(f"Unknown family: {family}")
    if np.isnan(x).all(axis=0).any():
        raise ValueError("All-missing training feature would change the eleven-feature schema")
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    )
    if family == "svm":
        if inner_splits is None:
            inner_splits = grouped_splits(x, y, groups, 20261123)
        model = CalibratedClassifierCV(
            estimator=model, cv=inner_splits, method="sigmoid", ensemble=False
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(x, y)
    except ConvergenceWarning as error:
        raise RuntimeError("Frozen fit failed convergence; no retuning/reseeding") from error
    return model


def oof_predict(params, x, y, groups, splits, inner):
    scores, coverage = np.full(len(y), np.nan), np.zeros(len(y), dtype=int)
    for index, (train, valid) in enumerate(splits):
        model = fit_model(params, x[train], y[train], groups[train], inner[index])
        scores[valid] = positive_scores(model, x[valid])
        coverage[valid] += 1
    if not np.all(coverage == 1) or not np.isfinite(scores).all():
        raise ValueError("OOF must cover every resolved study row exactly once with finite scores")
    return scores, coverage


def study_rows(world: dict) -> list[dict]:
    rows = [row for row in world["rows"] if row["phase"] == "study"]
    if not rows or len({row["loan_id"] for row in rows}) != len(rows):
        raise ValueError("Expected nonempty study rows with unique fictional loan IDs")
    if any(row["origen"] != "simulado" for row in rows):
        raise ValueError("Only synthetic rows are allowed")
    return rows


def feature_matrix(rows):
    # Unknown targets are placeholders only for the pure matrix helper, never for evaluation.
    return matrix([{**row, "late_payment": 0} for row in rows])[0]


def raw_metrics(y, scores, threshold):
    if len(y):
        return metrics(np.asarray(y, dtype=int), scores, threshold)
    return {
        "n": 0,
        **dict.fromkeys(
            ["precision", "recall", "f1", "f2", "accuracy", "balanced_accuracy", "roc_auc", "brier"]
        ),
        "confusion_matrix": [[0, 0], [0, 0]],
        "confusion_labels": [0, 1],
    }


def review_policy(rows, scores, threshold: float, spec: dict) -> tuple[np.ndarray, dict]:
    """Capacity uses all granted study rows, including unresolved labels."""
    if len(rows) != len(scores) or not np.isfinite(scores).all():
        raise ValueError("Policy requires one finite cached score per row")
    days = defaultdict(list)
    for index, row in enumerate(rows):
        at = datetime.fromisoformat(row["evaluated_at"])
        if at.tzinfo is not None:
            at = at.astimezone(ZoneInfo("America/Lima"))
        days[(row["replica_id"], at.date().isoformat())].append(index)
    actions = np.zeros(len(rows), dtype=int)
    daily = []
    for (replica, day), indices in sorted(days.items()):
        queue = sorted(
            [i for i in indices if scores[i] >= threshold],
            key=lambda i: (-float(scores[i]), rows[i]["loan_id"]),
        )
        accepted = queue[: spec["daily_cap"]]
        actions[accepted] = 1
        daily.append(
            {
                "replica_id": replica,
                "evaluation_civil_date": day,
                "before_cap": len(queue),
                "reviews": len(accepted),
                "minutes_hypothetical": len(accepted) * spec["minutes_per_case"],
            }
        )
    known = np.asarray([row["late_payment"] is not None for row in rows])
    y = np.asarray([row["late_payment"] for row in rows if row["late_payment"] is not None])
    predicted = actions[known]
    tp = int(np.sum((y == 1) & (predicted == 1)))
    tn = int(np.sum((y == 0) & (predicted == 0)))
    fp = int(np.sum((y == 0) & (predicted == 1)))
    fn = int(np.sum((y == 1) & (predicted == 0)))
    # Actions are not probabilities: compute classification metrics only, with beta=2.
    action_metrics = {
        "n": len(y),
        "precision": tp / (tp + fp or 1) if len(y) else None,
        "recall": tp / (tp + fn or 1) if len(y) else None,
        "f1": 2 * tp / (2 * tp + fp + fn or 1) if len(y) else None,
        "f2": 5 * tp / (5 * tp + fp + 4 * fn or 1) if len(y) else None,
        "accuracy": (tp + tn) / len(y) if len(y) else None,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "confusion_labels": [0, 1],
    }
    per_replica = {}
    for replica in sorted({row["replica_id"] for row in rows}):
        replica_days = [day for day in daily if day["replica_id"] == replica]
        per_replica[replica] = {
            "reviews": sum(day["reviews"] for day in replica_days),
            "daily_max": max((day["reviews"] for day in replica_days), default=0),
            "days_over_before_cap": sum(
                day["before_cap"] > spec["daily_cap"] for day in replica_days
            ),
            "minutes_hypothetical": sum(day["minutes_hypothetical"] for day in replica_days),
        }
    return actions, {
        "metrics": action_metrics,
        "reviews": int(actions.sum()),
        "reviews_known": int(actions[known].sum()),
        "reviews_unknown": int(actions[~known].sum()),
        "daily_max": max((day["reviews"] for day in daily), default=0),
        "days_over_before_cap": sum(day["before_cap"] > spec["daily_cap"] for day in daily),
        "capacity_respected": all(day["reviews"] <= spec["daily_cap"] for day in daily),
        "minutes_hypothetical": int(actions.sum()) * spec["minutes_per_case"],
        "daily": daily,
        "daily_key": ["replica_id", "evaluation_civil_date"],
        "per_replica": per_replica,
        "aggregation_note": "Alternative scenario totals, not simultaneous business volume",
        "scope": "Hypothetical granted-loan alerts only, not business approval or measured savings",
    }


def evaluate_cached(rows, scores, threshold, spec, include_predictions=False):
    known = np.asarray([row["late_payment"] is not None for row in rows])
    y = [row["late_payment"] for row in rows if row["late_payment"] is not None]
    actions, policy = review_policy(rows, scores, threshold, spec)
    result = {
        "metrics": raw_metrics(y, np.asarray(scores)[known], threshold),
        "review_policy": policy,
    }
    if include_predictions:
        predictions, errors = [], []
        for row, score, action in zip(rows, scores, actions, strict=True):
            case = {
                "origen": "simulado",
                "replica_id": row["replica_id"],
                "loan_id": row["loan_id"],
                "client_id": row["client_id"],
                "evaluated_at": row["evaluated_at"],
                "actual": row["late_payment"],
                "probability": float(score),
                "threshold": threshold,
                "predicted": int(score >= threshold),
                "review": int(action),
                "features": {name: row[name] for name in FEATURE_NAMES},
            }
            predictions.append(case)
            if case["actual"] is not None and (
                case["actual"] != case["predicted"] or case["actual"] != case["review"]
            ):
                errors.append(
                    {
                        **case,
                        "raw_error": None
                        if case["actual"] == case["predicted"]
                        else ("FP" if case["predicted"] else "FN"),
                        "policy_error": None
                        if case["actual"] == case["review"]
                        else ("FP" if case["review"] else "FN"),
                    }
                )
        result.update(
            {
                "predictions": predictions,
                "error_count": len(errors),
                "error_cases": errors[:10],
                "error_cases_note": "First up to ten actual raw/policy errors from cache; "
                "fewer than three only when fewer than three exist",
            }
        )
    return result


def select_candidate(entries):
    def rank(entry):
        policy = entry["review_policy"]
        value = policy["metrics"]
        return (
            value["f2"],
            value["recall"],
            value["precision"],
            value["f1"],
            -policy["reviews"],
            -entry["candidate_index"],
            -round(abs(entry["threshold"] - 0.5), 12),
        )

    return copy.deepcopy(max(entries, key=rank))


def write_rows_csv(path, rows):
    fields = [
        "origen",
        "replica_id",
        "phase",
        "loan_id",
        "client_id",
        "evaluated_at",
        "late_payment",
        *FEATURE_NAMES,
    ]
    with path.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def source_audit_pass(audit, protocol):
    targets = protocol["alignment_audit"]["approximate_grant_targets"]
    grants, clients = audit["mean_weekly_study_grants"], audit["mean_weekly_study_grant_clients"]
    return (
        audit["hard_constraints_pass"] is True
        and audit["grant_scale_pass"] is True
        and np.isfinite(grants)
        and np.isfinite(clients)
        and abs(grants - targets["weekly_loans"])
        <= (targets["weekly_loans"] * targets["relative_tolerance"])
        and abs(clients - targets["weekly_distinct_clients"]) <= targets["absolute_tolerance"]
    )


def baseline_comparison(models, selected):
    result = {}
    for split in ("train", "oof", "final"):
        policy = models[selected]["review_policy"][split]
        value = policy["metrics"]["f2"]
        references = {
            name: {
                "policy_f2": models[name]["review_policy"][split]["metrics"]["f2"],
                "strictly_beaten": value is not None
                and models[name]["review_policy"][split]["metrics"]["f2"] is not None
                and value > models[name]["review_policy"][split]["metrics"]["f2"],
            }
            for name in BASELINES
        }
        improves = all(item["strictly_beaten"] for item in references.values())
        result[split] = {
            "selected_ml_family": selected,
            "selected_policy_f2": value,
            "references": references,
            "proposed_ml_f2_improves_both": improves,
            "capacity_respected": policy["capacity_respected"],
            "proposal_pass": improves and policy["capacity_respected"],
            "failure": not (improves and policy["capacity_respected"]),
            "caveat": "Descriptive synthetic comparison, not real validation or business approval",
        }
    return result


def predict(artifact_dir: Path, input_data: dict) -> dict:
    """Load only trusted local evidence. This mode never imports the generator."""
    if not isinstance(input_data, dict):
        raise ValueError("Input must be an object containing exactly the eleven features")
    features = input_data.get("features", input_data)
    if not isinstance(features, dict) or set(features) != set(FEATURE_NAMES):
        raise ValueError("Input must contain exactly the eleven features, no label")
    if "features" in input_data and set(input_data) != {"features"}:
        raise ValueError("Input wrapper must contain features only")
    for name, value in features.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite nonnegative number or null")
        try:
            finite = np.isfinite(float(value))
        except OverflowError:
            finite = False
        if not finite or value < 0:
            raise ValueError(f"{name} must be a finite nonnegative number or null")
        if name in FEATURE_NAMES[:5] + ["tenure_days"] and int(value) != value:
            raise ValueError(f"{name} must be integral")
        if name in ("utilization", "requested_ratio", "punctuality_rate", "overdue_rate"):
            if value > 1 or (name == "requested_ratio" and value == 0):
                raise ValueError(f"{name} outside allowed ratio range")
    if features["paid_credits"] is not None and features["paid_late"] is not None:
        if features["paid_late"] > features["paid_credits"]:
            raise ValueError("paid_late cannot exceed paid_credits")
    manifest = json.loads((artifact_dir / "artifact_manifest.json").read_bytes())
    frozen_bytes = (artifact_dir / "frozen_selection.json").read_bytes()
    model_bytes = (artifact_dir / "selected_model.joblib").read_bytes()
    for name, data in (
        ("frozen_selection.json", frozen_bytes),
        ("selected_model.joblib", model_bytes),
    ):
        if sha256(data) != manifest[name]:
            raise ValueError(f"{name} SHA256 mismatch; refusing deserialization")
    frozen = json.loads(frozen_bytes)
    if frozen["feature_names"] != FEATURE_NAMES or frozen["version"] != "academic-owner-aligned-v4":
        raise ValueError("Artifact feature schema/version mismatch")
    model = joblib.load(io.BytesIO(model_bytes))
    vector = [
        [np.nan if features[name] is None else float(features[name]) for name in FEATURE_NAMES]
    ]
    score = float(positive_scores(model, vector)[0])
    if not np.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("Artifact returned invalid probability")
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
        "business_approval": False,
        "review_policy_note": "Threshold only; daily queue requires all cases + replica/date",
    }


def run(calibration_path: Path, protocol_path: Path, output: Path) -> dict:
    calibration_bytes, protocol_bytes = calibration_path.read_bytes(), protocol_path.read_bytes()
    validate_sources(calibration_bytes, protocol_bytes)
    anchors, protocol = json.loads(calibration_bytes), json.loads(protocol_bytes)
    from app.ml.features import FEATURE_NAMES as app_feature_names
    from app.ml.owner_aligned_synthetic import (
        generate_owner_aligned_dataset,
        validate_owner_aligned_dataset,
    )

    if FEATURE_NAMES != app_feature_names:
        raise ValueError("Feature order must match the eleven current MVP features")
    # All source evidence is persisted before even the first development generation.
    if output.exists():
        raise ValueError("Output directory must be new; never reuse evidence")
    output = prepare_output(output)
    for name, data in (("calibration.json", calibration_bytes), ("protocol.json", protocol_bytes)):
        with (output / name).open("xb") as file:
            file.write(data)
    code_paths = {
        "runner": Path(__file__).resolve(),
        "pure_helpers": Path(inspect.getfile(matrix)),
        "generator": Path(inspect.getfile(generate_owner_aligned_dataset)),
        "validator": Path(inspect.getfile(validate_owner_aligned_dataset)),
        **{
            name: BACKEND / "app" / "ml" / f"{name}.py"
            for name in ("features", "outcomes", "synthetic")
        },
    }
    provenance = {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "protocol_sha256": sha256(protocol_bytes),
        "calibration_sha256": sha256(calibration_bytes),
        "source_anchors": anchors,
        "source_anchors_dict_sha256": digest(anchors),
        "source_policy": protocol["excluded_business_source"],
        "code_sha256": {name: sha256(path.read_bytes()) for name, path in code_paths.items()},
        "runtime": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
        "feature_names": FEATURE_NAMES,
        "replica_interpretation": protocol["replica_interpretation"],
        "development_rows_scope": "Only resolved granted study rows; warmup/unresolved excluded. "
        "All rows remain in development_transactions.json and study CSV.",
        "old_data_policy": protocol["old_data_policy"],
    }
    write_json(output / "provenance.json", provenance)
    worlds, audits = [], []
    for spec in protocol["development_replicas"]:
        world = generate_owner_aligned_dataset(
            anchors, protocol["simulation"], spec["seed"], spec["prefix"]
        )
        worlds.append(world)
        audits.append(validate_owner_aligned_dataset(world, anchors, protocol["simulation"]))
    write_json(output / "development_transactions.json", {"replicas": worlds})
    write_json(output / "development_audits.json", audits)
    if len(worlds) != 2 or not all(source_audit_pass(audit, protocol) for audit in audits):
        raise ValueError("Development physical/grant mean scale audit failed; no fitting or final")
    all_study = [row for world in worlds for row in study_rows(world)]
    rows = [row for row in all_study if row["late_payment"] is not None]
    if len({row["loan_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate development loan IDs across replicas")
    client_sets = [{row["client_id"] for row in world["rows"]} for world in worlds]
    if client_sets[0] & client_sets[1]:
        raise ValueError("Alternative replicas must have distinct fictional client IDs")
    write_json(output / "development_rows.json", rows)
    write_rows_csv(output / "development_rows.csv", all_study)
    x, y = matrix(rows)
    groups = np.asarray([row["client_id"] for row in rows])
    splits = grouped_splits(x, y, groups, protocol["cv"]["seed"])
    inner = [
        grouped_splits(x[t], y[t], groups[t], protocol["svm_calibration"]["seed"])
        for t, _ in splits
    ]
    full_inner = grouped_splits(x, y, groups, protocol["svm_calibration"]["seed"])
    write_json(
        output / "fold_audit.json",
        {
            "index_space": "development_rows.json resolved study row order",
            "outer": fold_audit(splits, groups),
            "outer_fold_count": len(splits),
            "svm_outer_training_calibration": [
                {
                    "outer_fold": i,
                    "fold_count": len(inner[i]),
                    "folds": fold_audit(inner[i], groups[t], t),
                }
                for i, (t, _) in enumerate(splits)
            ],
            "svm_full_development_calibration": fold_audit(full_inner, groups),
        },
    )
    search, entries = [], []
    policy_spec = protocol["review_policy"]
    for index, params in enumerate(candidate_grid(protocol)):
        scores, coverage = oof_predict(params, x, y, groups, splits, inner)
        results = [
            {
                "family": params["family"],
                "candidate_index": index,
                "params": params,
                "threshold": threshold,
                **evaluate_cached(rows, scores, threshold, policy_spec),
            }
            for threshold in protocol["thresholds"]
        ]
        entries.extend(results)
        search.append(
            {
                "candidate_index": index,
                "params": params,
                "threshold_results": results,
                "oof_probabilities": scores.tolist(),
                "oof_prediction_counts": coverage.tolist(),
            }
        )
    baseline_oof = {}
    for name in BASELINES:
        scores, coverage = oof_predict({"family": name}, x, y, groups, splits, inner)
        baseline_oof[name] = {
            "params": {"family": name},
            "threshold": 0.5,
            **evaluate_cached(rows, scores, 0.5, policy_spec),
            "oof_probabilities": scores.tolist(),
            "oof_prediction_counts": coverage.tolist(),
        }
    write_json(
        output / "cv_search.json",
        {
            "candidates": search,
            "baselines": baseline_oof,
            "oof_limit": protocol["selection"]["oof_limit"],
            "unknown_limitation": "OOF excludes unknown loans and their queue competition",
        },
    )
    families = {
        name: select_candidate([e for e in entries if e["family"] == name]) for name in FAMILIES
    }
    winner = select_candidate(list(families.values()))
    frozen = {
        "version": protocol["version"],
        "frozen_utc": datetime.now(UTC).isoformat(),
        "feature_names": FEATURE_NAMES,
        "families": families,
        "global_winner": winner,
        "baselines": {
            name: {key: value for key, value in item.items() if not key.startswith("oof_")}
            for name, item in baseline_oof.items()
        },
        "decision_sha256": {
            name: sha256((output / name).read_bytes())
            for name in (
                "protocol.json",
                "calibration.json",
                "provenance.json",
                "development_transactions.json",
                "development_rows.json",
                "development_audits.json",
                "fold_audit.json",
                "cv_search.json",
            )
        },
        "source_anchors_dict_sha256": digest(anchors),
        "research_only": True,
        "oof_caveat": protocol["selection"]["oof_limit"],
        "selection_metric": "Capped review-policy F2, no minimum precision floor",
    }
    write_json(output / "frozen_selection.json", frozen)
    choices = {**families, **frozen["baselines"]}
    models, model_reports = {}, {}
    for name, choice in choices.items():
        model = fit_model(choice["params"], x, y, groups, full_inner)
        models[name] = model
        joblib.dump(model, output / f"{name}.joblib")
        train = evaluate_cached(rows, positive_scores(model, x), choice["threshold"], policy_spec)
        model_reports[name] = {
            "params": choice["params"],
            "threshold": choice["threshold"],
            "train": train["metrics"],
            "oof": choice["metrics"],
            "review_policy": {"train": train["review_policy"], "oof": choice["review_policy"]},
            "artifact": f"{name}.joblib",
            "interpretation": interpretation(model, name),
        }
    joblib.dump(models[winner["family"]], output / "selected_model.joblib")
    manifest = {
        name: sha256((output / name).read_bytes())
        for name in (
            "selected_model.joblib",
            "tree.joblib",
            "svm.joblib",
            "most_frequent.joblib",
            "constant_1.joblib",
            "frozen_selection.json",
        )
    }
    write_json(output / "artifact_manifest.json", manifest)

    # Boundary: all decisions, fits and model exports precede the one final generation.
    spec = protocol["final_replica"]
    final_world = generate_owner_aligned_dataset(
        anchors, protocol["simulation"], spec["seed"], spec["prefix"]
    )
    write_json(output / "final_transactions.json", final_world)
    try:
        final_audit = validate_owner_aligned_dataset(final_world, anchors, protocol["simulation"])
    except (AssertionError, ValueError) as error:
        final_audit = {
            "hard_constraints_pass": False,
            "grant_scale_pass": False,
            "mean_weekly_study_grants": None,
            "mean_weekly_study_grant_clients": None,
            "validator_error": f"{type(error).__name__}: {error}",
            "policy": "Preserve failed final evidence; never regenerate or tune",
        }
    write_json(output / "final_audits.json", final_audit)
    final_rows = study_rows(final_world)
    disjoint = not ({r["client_id"] for r in final_world["rows"]} & set.union(*client_sets))
    if not disjoint:
        raise ValueError("Final clients overlap development; no regeneration")
    xf = feature_matrix(final_rows)
    write_rows_csv(output / "final_rows.csv", final_rows)
    final_results = {}
    for name, model in models.items():
        # The sole final batch includes unknowns. All subsequent final analysis uses this cache.
        scores = positive_scores(model, xf)
        result = evaluate_cached(final_rows, scores, choices[name]["threshold"], policy_spec, True)
        final_results[name] = result
        model_reports[name]["final"] = result["metrics"]
        model_reports[name]["review_policy"]["final"] = result["review_policy"]
        for key in ("error_count", "error_cases", "error_cases_note"):
            model_reports[name][key] = result[key]
    write_json(output / "final_predictions.json", final_results)
    with (output / "final_predictions.csv").open("x", newline="", encoding="utf-8") as file:
        fields = [
            "model",
            "origen",
            "replica_id",
            "loan_id",
            "client_id",
            "evaluated_at",
            "actual",
            "probability",
            "threshold",
            "predicted",
            "review",
            *FEATURE_NAMES,
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for name, result in final_results.items():
            for case in result["predictions"]:
                writer.writerow(
                    {
                        "model": name,
                        **{k: v for k, v in case.items() if k != "features"},
                        **case["features"],
                    }
                )
    illustrative = protocol["illustrative_input"]
    duplicate = any(
        all(row[name] == illustrative[name] for name in FEATURE_NAMES)
        for world in [*worlds, final_world]
        for row in world["rows"]
    )
    write_json(output / "illustrative_input.json", {"features": illustrative})
    if duplicate:
        example = {
            "origen": "simulado",
            "research_only": True,
            "known_label": None,
            "illustrative_only": True,
            "business_approval": False,
            "distinctness_pass": False,
            "failure": "Frozen example duplicates a generated "
            "vector; not replaced or scored after final",
        }
    else:
        example = {
            **predict(output, {"features": illustrative}),
            "distinctness_pass": True,
            "requested_amount_pen": illustrative["requested_ratio"] * anchors["client_cap_pen"],
        }
    write_json(output / "illustrative_output.json", example)
    report = {
        "version": protocol["version"],
        "generated_utc": datetime.now(UTC).isoformat(),
        "origen": "simulado",
        "research_only": True,
        "business_approval": False,
        "target": protocol["target"],
        "feature_names": FEATURE_NAMES,
        "provenance": provenance,
        "selection": frozen,
        "development": {
            "audits": audits,
            "resolved_study_rows": len(rows),
            "unknown_study_rows": len(all_study) - len(rows),
            "replicas_are_alternative_histories": True,
            "development_rows_sha256": sha256((output / "development_rows.json").read_bytes()),
        },
        "final": {
            "audit": final_audit,
            "source_alignment_pass": source_audit_pass(final_audit, protocol),
            "study_rows": len(final_rows),
            "known_rows": sum(r["late_payment"] is not None for r in final_rows),
            "source_clients_disjoint": disjoint,
            "evaluation_batch_calls_per_model": dict.fromkeys(choices, 1),
            "policy": spec["policy"],
        },
        "models": model_reports,
        "baseline_comparison": baseline_comparison(model_reports, winner["family"]),
        "illustrative_inference": example,
        "artifact_sha256": manifest,
        "limitations": [
            protocol["scope"],
            protocol["replica_interpretation"],
            protocol["selection"]["oof_limit"],
            "OOF queue excludes unknown labels and misses their capacity competition",
            "F2 beta=2 and two-minute review times are assumptions, not measured costs",
            "Final source audit failure is reported without regeneration or tuning",
        ],
    }
    write_json(output / "aligned_v4_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in (
        "calibration",
        "protocol",
        "output-dir",
        "predict-artifact-dir",
        "input-json",
        "output-json",
    ):
        parser.add_argument(f"--{flag}", type=Path)
    args = parser.parse_args(argv)
    if args.predict_artifact_dir is not None:
        if (
            args.input_json is None
            or args.output_json is None
            or any(v is not None for v in (args.calibration, args.protocol, args.output_dir))
        ):
            parser.error("Inference requires input/output JSON and no experiment flags")
        if args.output_json.exists() or args.output_json.resolve().is_relative_to(BACKEND / "app"):
            parser.error("Inference output must be a new file outside production app")
        result = predict(args.predict_artifact_dir, json.loads(args.input_json.read_bytes()))
        write_json(args.output_json, result)
    else:
        if any(v is None for v in (args.calibration, args.protocol, args.output_dir)) or any(
            v is not None for v in (args.input_json, args.output_json)
        ):
            parser.error("Experiment requires calibration/protocol/output-dir only")
        result = run(args.calibration, args.protocol, args.output_dir)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
