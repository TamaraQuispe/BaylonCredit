"""Offline V6 research runner; import has no fitting or generation side effects.

Joblib requires a trusted local publisher. Hashes detect corruption, not malicious uploads.
Historical data-only authorization flags are evidence, never rewritten by this runner.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import sys
import warnings
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts import academic_credit_aligned_v4 as v4  # noqa: E402
from scripts import freeze_pending_v6_model_protocol as freeze  # noqa: E402
from scripts.academic_credit_grouped_cv import (  # noqa: E402
    FEATURE_NAMES,
    candidate_grid,
    interpretation,
    matrix,
    positive_scores,
    sha256,
    write_json,
)

VERSION = "academic-owner-pending-v6"
PROTOCOL_SHA256 = "eb7fcd39f69be0115895cbb43b6d84e4488535646108bd6f21381d0fb1607923"
BASELINES = ("most_frequent", "constant_1")
FAMILIES = ("tree", "svm")
MODEL_FILES = [f"{name}.joblib" for name in (*FAMILIES, *BASELINES)] + [
    "selected_model.joblib"]


def load_json(path):
    return json.loads(path.read_bytes())


def hashes(directory, names):
    return {name: sha256((directory / name).read_bytes()) for name in sorted(names)}


def verify_hashes(directory, expected):
    for name, digest in expected.items():
        if Path(name).name != name or (directory / name).is_symlink():
            raise ValueError("Only local regular evidence files are allowed")
        if sha256((directory / name).read_bytes()) != digest:
            raise ValueError(f"{name} SHA256 mismatch; refusing deserialization/generation")


def validate_runtime(expected):
    actual = {"python": platform.python_version(), **{
        key: version("scikit-learn" if key == "sklearn" else key)
        for key in freeze.RUNTIME if key != "python"}}
    if expected != freeze.RUNTIME or actual != expected:
        raise ValueError(f"Frozen runtime mismatch: {actual}")
    return actual


def load_sources(development, snapshot):
    """Read the original DEV bytes and exact saved partitions, never regenerate DEV."""
    if not __debug__:
        raise RuntimeError("Frozen validation requires assertions enabled")
    audit = freeze.audit
    before, saved = audit.inventory(development), audit.inventory(snapshot)
    assert sha256((snapshot / freeze.MODEL_PROTOCOL).read_bytes()) == PROTOCOL_SHA256
    protocol = load_json(snapshot / freeze.MODEL_PROTOCOL)
    manifest = load_json(development / "manifest.json")
    assert manifest["files"] == {n: h for n, h in before.items() if n != "manifest.json"}
    snapshot_manifest = load_json(snapshot / "manifest.json")
    assert snapshot_manifest["files"] == {n: h for n, h in saved.items() if n != "manifest.json"}
    expected = dict(zip([
        "development_manifest_sha256", "development_complete_csv_sha256",
        "development_labeled_csv_sha256", "development_gate_sha256", "fold_plan_sha256",
        "anchors_sha256", "owner_review_sha256", "data_protocol_sha256",
        "generator_sha256", "data_preparation_script_sha256"], [
        before["manifest.json"], before["desarrollo.csv"], before["desarrollo_etiquetado.csv"],
        saved["summaryauditoria-dev-v6.json"], saved["pliegues-planificados.json"],
        *[before[n] for n in audit.INPUTS],
        audit.FROZEN_CODE["/app/app/ml/owner_pending_synthetic.py"],
        audit.FROZEN_CODE["/app/scripts/prepare_pending_v6_data.py"]], strict=True))
    freeze.validate_protocol(protocol, expected)
    for name, digest in audit.INPUTS.items():
        assert before[name] == saved[name] == digest
    for name, digest in audit.FROZEN_CODE.items():
        assert audit.sha(BACKEND / name.removeprefix("/app/")) == digest
    gate = load_json(snapshot / "summaryauditoria-dev-v6.json")
    historical = load_json(snapshot / "preparation_plan.json")
    assert gate["technical_dev_gate_pass"] is gate["source_unchanged"] is True
    assert gate["source_hashes_before"] == gate["source_hashes_after"] == before
    assert historical["model_fit_performed"] is historical["final_generated"] is False
    assert historical["models_authorized"] is False
    assert historical["model_protocol_sha256"] == PROTOCOL_SHA256
    preparation = load_json(development / "preparation_plan.json")
    data = load_json(snapshot / "APF3_PENDING_V6_DATA_PROTOCOL.json")
    assert preparation["models_authorized"] is data["models_authorized"] is False
    assert preparation["final_seed"] is data["final_seed"] is None
    assert preparation["candidates"] == data["development_candidates"]
    assert protocol["final_replica"]["seed"] not in {
        c["seed"] for c in preparation["candidates"]}
    study = freeze.read_rows(development / "desarrollo.csv")
    known = freeze.read_rows(development / "desarrollo_etiquetado.csv")
    assert known == [r for r in study if r["late_payment"] is not None]
    assert (len(study), len(known), sum(r["late_payment"] == 0 for r in known),
            sum(r["late_payment"] == 1 for r in known)) == (545, 541, 454, 87)
    assert len({r["client_id"] for r in study}) == 24
    assert {r["replica_id"] for r in study} == set(protocol["development"]["replicas"])
    assert all(not r[k].startswith(protocol["final_replica"]["prefix"])
               for r in study for k in ("client_id", "loan_id"))
    plan = load_json(snapshot / "pliegues-planificados.json")
    freeze.validate_saved_folds(plan, known, study)
    validate_runtime(protocol["runtime"])
    from app.ml.features import FEATURE_NAMES as application_features

    assert FEATURE_NAMES == application_features == protocol["feature_names"]
    worlds = [load_json(development / f"{prefix}_transactions.json")
              for prefix in protocol["development"]["replicas"]]
    originals = [r for w in worlds for r in w["rows"] if r["phase"] == "study"]
    assert len(originals) == len(study)
    for original, row in zip(originals, study, strict=True):
        assert set(original) == set(row) == audit.ROW_KEYS
        assert all(original[k] == row[k] for k in (*FEATURE_NAMES, "loan_id", "late_payment"))
    return protocol, plan, known, study, worlds, before, saved


def local_inner(split, parent, known):
    """Saved inner indices are global in labeled CSV; sklearn expects training-local indices."""
    positions = {int(global_index): local for local, global_index in enumerate(parent)}
    if len(positions) != len(parent) or len(split["folds"]) != 3:
        raise ValueError("Expected three exact saved inner folds and unique parent indices")
    result, seen = [], []
    for fold in split["folds"]:
        train, valid = fold["train_indices"], fold["validation_indices"]
        if set(train) & set(valid) or set(train) | set(valid) != set(positions):
            raise ValueError("Inner fold escapes outer training subset")
        if {known[i]["client_id"] for i in train} & {known[i]["client_id"] for i in valid}:
            raise ValueError("Inner client leakage")
        for indices in (train, valid):
            if {known[i]["late_payment"] for i in indices} != {0, 1}:
                raise ValueError("Both known classes required in every inner subset")
        result.append((np.array([positions[i] for i in train]),
                       np.array([positions[i] for i in valid])))
        seen.extend(valid)
    if sorted(seen) != sorted(parent):
        raise ValueError("Inner validation coverage must be exactly one")
    return result


def fit_model(params, x, y, groups, inner):
    options = {k: v for k, v in params.items() if k != "family"}
    family = params["family"]
    if np.isnan(x).all(axis=0).any():
        raise ValueError("All-missing training feature; refusing schema change")
    if family == "tree":
        classifier = DecisionTreeClassifier(**options)
    elif family == "svm":
        if options.get("kernel") != "linear" or options.get("probability") is not False:
            raise ValueError("SVM requires linear margin and saved sigmoid calibration")
        classifier = SVC(**options)
    elif family in BASELINES:
        classifier = (DummyClassifier(strategy="most_frequent") if family == "most_frequent"
                      else DummyClassifier(strategy="constant", constant=1))
    else:
        raise ValueError("Unknown model family")
    model = Pipeline([("imputer", SimpleImputer(strategy="median")),
                      ("scaler", StandardScaler()), ("classifier", classifier)])
    if family == "svm":
        if inner is None or len(inner) != 3:
            raise ValueError("SVM requires exactly three saved inner folds; no seed fallback")
        coverage = np.zeros(len(y), dtype=int)
        for train, valid in inner:
            if (set(train) & set(valid) or set(train) | set(valid) != set(range(len(y)))
                    or set(groups[train]) & set(groups[valid])):
                raise ValueError("Calibration partition/client leakage")
            if np.isnan(x[train]).all(axis=0).any():
                raise ValueError("All-missing inner training feature")
            if len(np.unique(y[train])) != 2 or len(np.unique(y[valid])) != 2:
                raise ValueError("Calibration requires both classes")
            coverage[valid] += 1
        if not np.all(coverage == 1):
            raise ValueError("Calibration coverage must be exactly one")
        model = CalibratedClassifierCV(estimator=model, cv=inner, method="sigmoid", ensemble=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(x, y)
    return model


def checked_scores(model, x):
    scores = np.asarray(positive_scores(model, x), dtype=float)
    if scores.shape != (len(x),) or not np.isfinite(scores).all() or (
            (scores < 0) | (scores > 1)).any():
        raise ValueError("Expected one finite positive-class probability per input row")
    return scores


def oof_predict(params, known, study, plan):
    x, y = matrix(known)
    xs = v4.feature_matrix(study)
    groups = np.asarray([r["client_id"] for r in known])
    scores, coverage, assignments = (np.full(len(study), np.nan),
                                      np.zeros(len(study), dtype=int),
                                      np.full(len(study), -1, dtype=int))
    for number, fold in enumerate(plan["outer"]["folds"]):
        train = np.asarray(fold["train_indices"])
        clients = set(fold["validation_clients"])
        valid = np.asarray([i for i, r in enumerate(study) if r["client_id"] in clients])
        if set(groups[train]) & clients:
            raise ValueError("Outer client leakage")
        inner = local_inner(plan["inner_sigmoid_by_outer_train"][number], train, known)
        model = fit_model(params, x[train], y[train], groups[train], inner)
        scores[valid] = checked_scores(model, xs[valid])
        coverage[valid] += 1
        assignments[valid] = number
    if not np.all(coverage == 1) or not np.isfinite(scores).all():
        raise ValueError("OOF must cover all study rows, including unknowns, exactly once")
    return scores, coverage, assignments


def evaluate_cached(rows, scores, threshold, spec, assignments=None, predictions=False):
    # Sort before using the V4 pure cache helper so errors are deterministic, not source ordered.
    if assignments is None:
        indices = sorted(range(len(rows)), key=lambda i: rows[i]["loan_id"])
        return v4.evaluate_cached([rows[i] for i in indices], np.asarray(scores)[indices],
                                  threshold, spec, predictions)
    assignments = np.asarray(assignments)
    actions = np.zeros(len(rows), dtype=int)
    folds = []
    daily = []
    for number in sorted(set(assignments.tolist())):
        indices = np.flatnonzero(assignments == number)
        subset = [rows[i] for i in indices]
        fold_actions, policy = v4.review_policy(
            subset, np.asarray(scores)[indices], threshold, spec)
        actions[indices] = fold_actions
        folds.append({"outer_fold": number, **v4.evaluate_cached(
            subset, np.asarray(scores)[indices], threshold, spec)})
        daily.extend({"outer_fold": number, **day} for day in policy["daily"])
    known = np.asarray([r["late_payment"] is not None for r in rows])
    y = [r["late_payment"] for r in rows if r["late_payment"] is not None]
    policy_metrics = v4.raw_metrics(y, actions[known], 0.5)
    policy_metrics = {k: v for k, v in policy_metrics.items()
                      if k not in ("roc_auc", "brier", "balanced_accuracy")}
    return {"metrics": v4.raw_metrics(y, np.asarray(scores)[known], threshold),
            "fold_metrics": folds,
            "review_policy": {
                "metrics": policy_metrics, "reviews": int(actions.sum()),
                "reviews_known": int(actions[known].sum()),
                "reviews_unknown": int(actions[~known].sum()),
                "daily_max": max((d["reviews"] for d in daily), default=0),
                "days_over_before_cap": sum(d["before_cap"] > spec["daily_cap"] for d in daily),
                "capacity_respected": all(d["reviews"] <= spec["daily_cap"] for d in daily),
                "minutes_hypothetical": int(actions.sum()) * spec["minutes_per_case"],
                "daily": daily,
                "daily_key": ["outer_fold", "replica_id", "evaluation_civil_date"],
                "scope": freeze.QUEUE_SCOPE}}


def rank(entry):
    policy = entry["review_policy"]
    m = policy["metrics"]
    return (m["f2"], m["recall"], m["precision"], m["f1"], -policy["reviews"],
            -entry["candidate_index"], -round(abs(entry["threshold"] - 0.5), 12),
            -entry["threshold"])


def validate_features(input_data):
    if not isinstance(input_data, dict):
        raise ValueError("Input must contain exactly eleven features, no label")
    features = input_data.get("features", input_data)
    if (not isinstance(features, dict) or set(features) != set(FEATURE_NAMES)
            or ("features" in input_data and set(input_data) != {"features"})):
        raise ValueError("Input must contain exactly eleven features, no label")
    for name, value in features.items():
        if value is None:
            continue
        try:
            valid = type(value) in (int, float) and np.isfinite(float(value)) and value >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"{name} must be finite nonnegative numeric or null")
        if name in FEATURE_NAMES[:5] + ["tenure_days"] and int(value) != value:
            raise ValueError(f"{name} must be integral")
        if name in ("utilization", "requested_ratio", "punctuality_rate", "overdue_rate"):
            if value > 1 or (name == "requested_ratio" and value == 0):
                raise ValueError(f"{name} outside allowed ratio range")
    for name in ("pending_overdue", "pending_current", "outstanding", "utilization",
                 "overdue_rate"):
        if features[name] is None or features[name] != 0:
            raise ValueError("Not eligible / outside V6 domain: pending features must be "
                             "known zero; no model called")
    paid, late, sales = (features[n] for n in ("paid_credits", "paid_late", "completed_sales"))
    if paid is not None and late is not None and late > paid:
        raise ValueError("paid_late cannot exceed paid_credits")
    if sales is not None and paid is not None and sales != paid:
        raise ValueError("Outside V6 credit-only sales domain; cash-sale history is unmeasured")
    punctuality = features["punctuality_rate"]
    if paid is not None and late is not None and punctuality is not None:
        expected = (paid - late) / paid if paid else 0.0
        if not np.isclose(punctuality, expected, rtol=0, atol=1e-9):
            raise ValueError("punctuality_rate inconsistent with paid history")
    return features


def verify_freeze(directory):
    frozen = load_json(directory / "freeze_before_final.json")
    verify_hashes(directory, frozen["files"])
    selection = load_json(directory / "frozen_selection.json")
    verify_hashes(directory, selection["decision_sha256"])
    manifest = load_json(directory / "artifact_manifest.json")
    if set(manifest) != set(MODEL_FILES + ["frozen_selection.json", "protocol.json"]):
        raise ValueError("Incomplete artifact manifest")
    if not set(manifest) <= set(frozen["files"]):
        raise ValueError("Artifacts absent from persisted freeze")
    verify_hashes(directory, manifest)
    protocol = load_json(directory / "protocol.json")
    if sha256((directory / "protocol.json").read_bytes()) != PROTOCOL_SHA256:
        raise ValueError("Unsupported frozen model protocol SHA256")
    if (selection["version"] != VERSION or selection["feature_names"] != FEATURE_NAMES
            or protocol["feature_names"] != FEATURE_NAMES):
        raise ValueError("Artifact feature order/schema/version mismatch")
    validate_runtime(protocol["runtime"])
    winner = selection["global_winner"]
    if (winner["family"] not in FAMILIES or winner["threshold"] not in protocol["thresholds"]
            or winner["params"] not in candidate_grid(protocol)
            or winner != selection["families"][winner["family"]]
            or winner != max(selection["families"].values(), key=rank)):
        raise ValueError("Frozen winner inconsistent with protocol/selection")
    if manifest["selected_model.joblib"] != manifest[f"{winner['family']}.joblib"]:
        raise ValueError("Selected artifact differs from frozen winning family")
    search = load_json(directory / "cv_search.json")
    for family in FAMILIES:
        candidates = [entry for candidate in search["candidates"]
                      for entry in candidate["threshold_results"] if entry["family"] == family]
        if selection["families"][family] != max(candidates, key=rank):
            raise ValueError("Family winner differs from persisted OOF search")
    return selection


def predict(artifact_dir, input_data):
    """Trusted local inference only. Verify the complete evidence chain before joblib.load."""
    features = validate_features(input_data)
    selection = verify_freeze(artifact_dir)
    model = joblib.load(io.BytesIO((artifact_dir / "selected_model.joblib").read_bytes()))
    if (getattr(model, "n_features_in_", None) != 11
            or list(getattr(model, "classes_", [])) != [0, 1]):
        raise ValueError("Artifact must have eleven inputs and binary classes [0, 1]")
    winner = selection["global_winner"]
    estimator = model
    if winner["family"] == "svm":
        if (not isinstance(model, CalibratedClassifierCV) or model.method != "sigmoid"
                or model.ensemble is not False):
            raise ValueError("Expected frozen sigmoid SVM artifact")
        estimator = model.estimator
    if not isinstance(estimator, Pipeline) or list(estimator.named_steps) != [
            "imputer", "scaler", "classifier"]:
        raise ValueError("Expected frozen preprocessing Pipeline")
    if (not isinstance(estimator.named_steps["imputer"], SimpleImputer)
            or estimator.named_steps["imputer"].strategy != "median"
            or not isinstance(estimator.named_steps["scaler"], StandardScaler)):
        raise ValueError("Artifact preprocessing differs from frozen protocol")
    classifier = estimator.named_steps["classifier"]
    expected_class = DecisionTreeClassifier if winner["family"] == "tree" else SVC
    if not isinstance(classifier, expected_class) or any(
            classifier.get_params()[k] != v for k, v in winner["params"].items() if k != "family"):
        raise ValueError("Model family/parameters differ from frozen selection")
    score = float(checked_scores(model, v4.feature_matrix([features]))[0])
    return {"version": VERSION, "origen": "simulado", "illustrative_only": True,
            "known_label": None, "family": winner["family"], "feature_names": FEATURE_NAMES,
            "features": features, "probability": score, "threshold": winner["threshold"],
            "predicted": int(score >= winner["threshold"]), "research_only": True,
            "business_approval": False, "review_policy_applied": False,
            "review_policy_note": "Threshold only; daily queue requires all cases and replica/date"}


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(development, snapshot, output):
    development, snapshot, output = (Path(p).resolve() for p in (development, snapshot, output))
    if output.exists():
        raise ValueError("Output directory must be new; never reuse evidence")
    if (not output.parent.is_dir() or output.is_relative_to(BACKEND)
            or output.is_relative_to(development) or output.is_relative_to(snapshot)):
        raise ValueError("Output requires existing parent outside source directories")
    protocol, plan, known, study, worlds, before, saved = load_sources(development, snapshot)
    output.mkdir()
    copies = {"protocol.json": snapshot / freeze.MODEL_PROTOCOL,
              "data_protocol.json": snapshot / "APF3_PENDING_V6_DATA_PROTOCOL.json",
              "calibration.json": snapshot / "APF3_OWNER_ANCHORS_V4.json",
              "owner_review.json": snapshot / "APF3_OWNER_REVIEW_V5.json",
              "fold_audit.json": snapshot / "pliegues-planificados.json",
              "development_gate.json": snapshot / "summaryauditoria-dev-v6.json",
              "inputdevmanifest.json": development / "manifest.json",
              "historical_snapshot.json": snapshot / "preparation_plan.json",
              "development_audits.json": development / "development_audits.json"}
    copies.update({f"inputdev_{name}": development / name for name in before})
    copies.update({f"snapshot_{name}": snapshot / name for name in saved})
    for name, source in copies.items():
        (output / name).write_bytes(source.read_bytes())
    write_json(output / "inputdev_inventory.json", before)
    write_json(output / "snapshot_inventory.json", saved)
    write_json(output / "development_rows.json", known)
    write_json(output / "development_study_rows.json", study)
    write_json(output / "development_transactions.json", {"replicas": worlds})
    write_csv(output / "development_rows.csv", study)
    code = {str(p.relative_to(BACKEND)): freeze.audit.sha(p) for p in [
        *[BACKEND / n.removeprefix("/app/") for n in freeze.audit.FROZEN_CODE],
        Path(__file__), Path(freeze.__file__), Path(freeze.audit.__file__), Path(v4.__file__),
        BACKEND / "scripts/academic_credit_grouped_cv.py"]}
    provenance = {"recorded_utc": datetime.now(UTC).isoformat(), "code_sha256": code,
                  "runtime": validate_runtime(protocol["runtime"]),
                  "input_sha256": hashes(output, copies),
                  "authorization": {"step": "separate_user_authorized_research_execution",
                                    "historical_snapshot_models_authorized": False,
                                    "historical_protocol_unchanged": True,
                                    "business_approval": False},
                  "source_quality": load_json(output / "development_gate.json"),
                  "source_anchors": load_json(output / "calibration.json"),
                  "source_review": load_json(output / "owner_review.json")}
    write_json(output / "provenance.json", provenance)
    search, entries, baseline_oof = [], [], {}
    spec = protocol["review_policy"]
    for index, params in enumerate(candidate_grid(protocol) + [{"family": n} for n in BASELINES]):
        scores, coverage, assignments = oof_predict(params, known, study, plan)
        thresholds = protocol["thresholds"] if params["family"] in FAMILIES else [0.5]
        results = [{"family": params["family"], "candidate_index": index, "params": params,
                    "threshold": t, **evaluate_cached(study, scores, t, spec, assignments)}
                   for t in thresholds]
        item = {"candidate_index": index, "params": params, "threshold_results": results,
                "oof_probabilities": scores.tolist(), "oof_prediction_counts": coverage.tolist(),
                "outer_fold": assignments.tolist()}
        if params["family"] in FAMILIES:
            search.append(item)
            entries.extend(results)
        else:
            baseline_oof[params["family"]] = {**results[0], **item}
    write_json(output / "cv_search.json", {"candidates": search, "baselines": baseline_oof,
               "study_loan_ids": [r["loan_id"] for r in study],
               "oof_queue_scope": freeze.QUEUE_SCOPE,
               "selection_optimism": protocol["cv"]["selection_optimism"]})
    families = {name: max([e for e in entries if e["family"] == name], key=rank)
                for name in FAMILIES}
    winner = max(families.values(), key=rank)
    choices = {**families, **baseline_oof}
    x, y = matrix(known)
    xs = v4.feature_matrix(study)
    groups = np.asarray([r["client_id"] for r in known])
    inner = local_inner(plan["inner_sigmoid_full_train"], range(len(known)), known)
    models, reports = {}, {}
    for name, choice in choices.items():
        model = fit_model(choice["params"], x, y, groups, inner)
        models[name] = model
        joblib.dump(model, output / f"{name}.joblib")
        train = evaluate_cached(study, checked_scores(model, xs), choice["threshold"], spec)
        reports[name] = {"params": choice["params"], "threshold": choice["threshold"],
                         "train": train["metrics"], "oof": choice["metrics"],
                         "review_policy": {"train": train["review_policy"],
                                           "oof": choice["review_policy"]},
                         "train_note": "Descriptive fitted predictions, not independent evaluation",
                         "artifact": f"{name}.joblib",
                         "interpretation": interpretation(model, name)}
    (output / "selected_model.joblib").write_bytes(
        (output / f"{winner['family']}.joblib").read_bytes())
    write_json(output / "training_reports.json", reports)
    selection = {"version": VERSION, "feature_names": FEATURE_NAMES, "families": families,
                 "global_winner": winner,
                 "baselines": {n: {k: v for k, v in c.items() if not k.startswith("oof_")}
                               for n, c in baseline_oof.items()},
                 "decision_sha256": hashes(output, [p.name for p in output.iterdir()]),
                 "research_only": True}
    write_json(output / "frozen_selection.json", selection)
    manifest = hashes(output, MODEL_FILES + ["frozen_selection.json", "protocol.json"])
    write_json(output / "artifact_manifest.json", manifest)
    write_json(output / "freeze_before_final.json", {
        "version": VERSION, "frozen_utc": datetime.now(UTC).isoformat(),
        "files": hashes(output, [p.name for p in output.iterdir()]),
        "final_generation_calls": 0, "final_prediction_calls": 0})
    verify_freeze(output)
    # FINAL uses the persisted estimators, not merely their still-live training objects.
    models = {name: joblib.load(io.BytesIO((output / f"{name}.joblib").read_bytes()))
              for name in choices}
    assert before == freeze.audit.inventory(development)
    assert saved == freeze.audit.inventory(snapshot)
    assert code == {name: freeze.audit.sha(BACKEND / name) for name in code}

    # No generator invocation exists above this persisted, reloaded hash boundary.
    from app.ml.owner_pending_synthetic import (
        generate_owner_pending_dataset,
        validate_owner_pending_dataset,
    )

    anchors = load_json(output / "calibration.json")
    data = load_json(output / "data_protocol.json")
    review = load_json(output / "owner_review.json")
    final_spec = protocol["final_replica"]
    try:
        world = generate_owner_pending_dataset(anchors, data["simulation"], review, data,
                                               final_spec["seed"], final_spec["prefix"])
        write_json(output / "final_transactions.json", world)
        final_audit = validate_owner_pending_dataset(
            world, anchors, data["simulation"], review, data)
        write_json(output / "final_audits.json", final_audit)
        if final_audit["hard_constraints_pass"] is not True:
            raise ValueError("Final hard validation failed")
        if {r["client_id"] for r in world["rows"]} & {
                r["client_id"] for w in worlds for r in w["rows"]}:
            raise ValueError("Final clients overlap DEV")
        if any(r[n] != 0 for r in world["rows"] for n in
               ("pending_overdue", "pending_current", "outstanding", "utilization",
                "overdue_rate")):
            raise ValueError("Granted final row has pending exposure")
        final_rows = v4.study_rows(world)
        xf = v4.feature_matrix(final_rows)
    except Exception as error:
        write_json(output / "failure.json", {"stage": "final_generation_or_hard_validation",
                   "error": f"{type(error).__name__}: {error}", "retry": False})
        raise
    write_csv(output / "final_rows.csv", final_rows)
    final_results, ledger = {}, {}
    for name, model in models.items():
        scores = checked_scores(model, xf)
        ledger[name] = {"batch_calls": 1, "rows_scored": len(final_rows),
                        "unknown_rows_scored": sum(r["late_payment"] is None for r in final_rows)}
        result = evaluate_cached(final_rows, scores, choices[name]["threshold"], spec,
                                 predictions=True)
        final_results[name] = {"scores": scores.tolist(),
                               "score_loan_ids": [r["loan_id"] for r in final_rows], **result}
        reports[name]["final"] = result["metrics"]
        reports[name]["review_policy"]["final"] = result["review_policy"]
        reports[name].update({k: result[k] for k in
                              ("error_count", "error_cases", "error_cases_note")})
    write_json(output / "final_predictions.json", final_results)
    write_json(output / "final_call_ledger.json", ledger)
    write_csv(output / "final_predictions.csv", [
        {"model": name, **{k: v for k, v in case.items() if k != "features"}, **case["features"]}
        for name, result in final_results.items() for case in result["predictions"]])
    illustrative = protocol["illustrative_input"]["features"]
    duplicate = any(all(r[n] == illustrative[n] for n in FEATURE_NAMES)
                    for w in [*worlds, world] for r in w["rows"])
    write_json(output / "illustrative_input.json", {"features": illustrative})
    example = ({"status": "omitted_duplicate", "distinctness_pass": False,
                "known_label": None, "research_only": True, "business_approval": False}
               if duplicate else {**predict(output, {"features": illustrative}),
                                  "distinctness_pass": True, "requested_amount_pen": 20})
    write_json(output / "illustrative_output.json", example)
    report = {"version": VERSION, "origen": "simulado", "research_only": True,
              "business_approval": False, "feature_names": FEATURE_NAMES,
              "provenance": provenance, "selection": selection,
              "development": {"study_rows": len(study), "known_rows": len(known),
                              "unknown_rows": len(study) - len(known),
                              "audits": load_json(output / "development_audits.json")},
              "final": {"audit": final_audit, "study_rows": len(final_rows),
                        "known_rows": sum(r["late_payment"] is not None for r in final_rows),
                        "source_clients_disjoint": True,
                        "evaluation_batch_calls_per_model": dict.fromkeys(models, 1),
                        "call_ledger": ledger},
              "models": reports,
              "baseline_comparison": v4.baseline_comparison(reports, winner["family"]),
              "illustrative_inference": example, "artifact_sha256": manifest,
              "limits": protocol["limits"] + [protocol["cv"]["selection_optimism"],
                                                "Undefined precision uses zero_division=0"]}
    write_json(output / "pending_v6_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("development-dir", "protocol-dir", "output-dir", "predict-artifact-dir",
                 "input-json", "output-json"):
        parser.add_argument(f"--{flag}", type=Path)
    args = parser.parse_args(argv)
    if args.predict_artifact_dir is not None:
        if (args.input_json is None or args.output_json is None or any(v is not None for v in
                (args.development_dir, args.protocol_dir, args.output_dir))):
            parser.error("Inference requires input/output JSON and no experiment flags")
        if args.output_json.exists() or args.output_json.resolve().is_relative_to(BACKEND):
            parser.error("Inference output must be new and outside backend source")
        result = predict(args.predict_artifact_dir, load_json(args.input_json))
        write_json(args.output_json, result)
        summary = {k: result[k] for k in
                   ("version", "family", "probability", "threshold", "predicted")}
    else:
        if (any(v is None for v in (args.development_dir, args.protocol_dir, args.output_dir))
                or args.input_json is not None or args.output_json is not None):
            parser.error("Experiment requires development-dir/protocol-dir/output-dir only")
        result = run(args.development_dir, args.protocol_dir, args.output_dir)
        winner = result["selection"]["global_winner"]
        summary = {"version": VERSION, "family": winner["family"], "threshold": winner["threshold"],
                   "development": {k: result["development"][k] for k in
                                   ("study_rows", "known_rows", "unknown_rows")},
                   "final_metrics": result["models"][winner["family"]]["final"],
                   "final_batch_calls": result["final"]["evaluation_batch_calls_per_model"]}
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
