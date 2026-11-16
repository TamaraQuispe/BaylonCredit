"""UNIT77/123 fixtures only. Never run the real DEV fit or the real final generator."""

from copy import deepcopy

import numpy as np
import pytest
from sklearn.calibration import CalibratedClassifierCV

from scripts import academic_credit_pending_v6 as runner

PREDICT = runner.predict
FIT = runner.fit_model


def features():
    return dict(zip(runner.FEATURE_NAMES, [6, 6, 1, 0, 0, 0, 0, 0.25, 60, 5 / 6, 0], strict=True))


def fixture_rows():
    known = [{**features(), "loan_id": f"UNIT77-L{c}-{label}", "client_id": f"UNIT77-C{c}",
              "late_payment": label, "phase": "study", "origen": "simulado",
              "replica_id": "UNIT77", "evaluated_at": "2026-01-01T09:00:00",
              "tenure_days": c * 10 + label}
             for c in range(9) for label in (0, 1)]
    study = known + [{**known[0], "loan_id": "UNIT77-U", "late_payment": None}]

    def split(parent):
        clients = sorted({known[i]["client_id"] for i in parent})
        return {"seed": 77, "folds": [
            {"train_indices": [i for i in parent if known[i]["client_id"] not in clients[n::3]],
             "validation_indices": [i for i in parent if known[i]["client_id"] in clients[n::3]],
             "validation_clients": clients[n::3]}
            for n in range(3)]}

    outer = split(list(range(len(known))))
    plan = {"outer": outer, "inner_sigmoid_by_outer_train": [
        split(f["train_indices"]) for f in outer["folds"]],
        "inner_sigmoid_full_train": split(list(range(len(known))))}
    return known, study, plan


def test_global_to_local_saved_indices_and_groups():
    known, _, plan = fixture_rows()
    parent = plan["outer"]["folds"][1]["train_indices"][::-1]
    split = plan["inner_sigmoid_by_outer_train"][1]
    result = runner.local_inner(split, parent, known)
    for (train, valid), original in zip(result, split["folds"], strict=True):
        assert [parent[i] for i in train] == original["train_indices"]
        assert [parent[i] for i in valid] == original["validation_indices"]
        assert {known[parent[i]]["client_id"] for i in train}.isdisjoint(
            {known[parent[i]]["client_id"] for i in valid})
    broken = deepcopy(split)
    broken["folds"][0]["train_indices"].append(999)
    with pytest.raises(ValueError, match="escapes"):
        runner.local_inner(broken, parent, known)


def test_oof_unknown_scored_never_fitted(monkeypatch):
    known, study, plan = fixture_rows()
    fits = []
    original = runner.fit_model

    def fit(params, x, y, groups, inner):
        assert len(x) == len(y) == len(groups) == 12
        assert set(y) == {0, 1}
        fits.append(set(groups))
        return original(params, x, y, groups, inner)

    monkeypatch.setattr(runner, "fit_model", fit)
    scores, coverage, assignment = runner.oof_predict({"family": "constant_1"}, known, study, plan)
    assert coverage.tolist() == [1] * len(study)
    assert scores.tolist() == [1] * len(study)
    assert assignment[-1] == assignment[0]
    for i, row in enumerate(study):
        assert row["client_id"] not in fits[assignment[i]]


def test_fold_queues_not_pooled_unknown_consumes_capacity():
    rows = [{**fixture_rows()[1][-1], "loan_id": f"UNIT77-{i:02}",
             "late_payment": None if i == 0 else i % 2} for i in range(12)]
    result = runner.evaluate_cached(rows, np.ones(12), 0.5,
                                    {"daily_cap": 5, "minutes_per_case": 2}, [0] * 6 + [1] * 6)
    policy = result["review_policy"]
    assert policy["reviews"] == 10
    assert policy["reviews_unknown"] == 1
    assert policy["reviews_known"] == 9
    assert result["metrics"]["n"] == 11
    assert policy["metrics"]["n"] == 11
    assert policy["daily_max"] == 5 and policy["days_over_before_cap"] == 2
    assert policy["daily_key"][0] == "outer_fold"
    assert len(result["fold_metrics"]) == 2
    for row in rows:
        row["late_payment"] = None
    unknown = runner.evaluate_cached(rows, np.ones(12), 0.5,
                                     {"daily_cap": 5, "minutes_per_case": 2}, [0] * 6 + [1] * 6)
    assert unknown["metrics"]["n"] == 0 and unknown["metrics"]["f2"] is None
    assert unknown["review_policy"]["metrics"]["f2"] is None
    assert unknown["review_policy"]["reviews_unknown"] == 10


def entry():
    return {"threshold": 0.4, "candidate_index": 3,
            "review_policy": {"reviews": 5, "metrics": dict.fromkeys(
                ("f2", "recall", "precision", "f1"), 0.5)}}


@pytest.mark.parametrize("criterion", ["f2", "recall", "precision", "f1", "reviews",
                                        "candidate_index", "distance", "threshold"])
def test_all_rank_tie_breakers(criterion):
    a, b = entry(), entry()
    if criterion in ("f2", "recall", "precision", "f1"):
        a["review_policy"]["metrics"][criterion] += 0.1
    elif criterion == "reviews":
        a["review_policy"]["reviews"] -= 1
    elif criterion == "candidate_index":
        a["candidate_index"] -= 1
    elif criterion == "distance":
        a["threshold"] = 0.5
    else:
        b["threshold"] = 0.6
    assert runner.rank(a) > runner.rank(b)


def test_error_cases_sorted_from_cache_without_model_calls():
    rows = [{**fixture_rows()[0][0], "loan_id": f"UNIT77-{n:02}", "late_payment": 1}
            for n in reversed(range(15))]
    result = runner.evaluate_cached(rows, np.zeros(15), 0.5,
                                    {"daily_cap": 5, "minutes_per_case": 2}, predictions=True)
    assert result["error_count"] == 15
    assert [c["loan_id"] for c in result["error_cases"]] == [f"UNIT77-{i:02}" for i in range(10)]


@pytest.mark.parametrize("name,value", [("paid_late", 7), ("requested_ratio", 0),
                                        ("completed_sales", 8), ("tenure_days", -1),
                                        ("paid_credits", 1.5), ("punctuality_rate", 0.1),
                                        ("requested_ratio", float("nan")),
                                        ("paid_late", True), ("tenure_days", 10**999)])
def test_invalid_features_rejected_before_artifacts(tmp_path, name, value):
    data = {**features(), name: value}
    with pytest.raises(ValueError):
        runner.predict(tmp_path, data)


@pytest.mark.parametrize("name", ["pending_current", "pending_overdue", "outstanding",
                                   "utilization", "overdue_rate"])
@pytest.mark.parametrize("value", [None, 1])
def test_pending_unknown_or_positive_fails_closed(tmp_path, name, value):
    with pytest.raises(ValueError, match="Not eligible"):
        runner.predict(tmp_path, {**features(), name: value})


def test_input_contract_and_missing_values():
    for data in ({**features(), "late_payment": None}, {"features": features(), "label": 1}, []):
        with pytest.raises(ValueError, match="eleven"):
            runner.validate_features(data)
    assert runner.validate_features({**features(), "tenure_days": 100000})["tenure_days"] == 100000
    assert runner.validate_features({**features(), "paid_late": None})["paid_late"] is None
    assert runner.validate_features({**features(), "paid_late": 0, "paid_credits": 0,
                                     "completed_sales": 0, "punctuality_rate": 0})


def test_positive_class_order_and_invalid_probability():
    class Reverse:
        classes_ = np.array([1, 0])

        def predict_proba(self, x):
            return np.tile([0.8, 0.2], (len(x), 1))

    assert runner.checked_scores(Reverse(), [[0]])[0] == 0.8

    class Invalid(Reverse):
        def predict_proba(self, x):
            return np.tile([float("nan"), 0], (len(x), 1))

    with pytest.raises(ValueError, match="finite"):
        runner.checked_scores(Invalid(), [[0]])


def test_tiny_real_svm_calibration_pipeline_saved_groups(monkeypatch):
    known, _, plan = fixture_rows()
    x, y = runner.matrix(known)
    x[0, 0] = np.nan
    groups = np.array([r["client_id"] for r in known])
    inner = runner.local_inner(plan["inner_sigmoid_full_train"], range(len(y)), known)
    params = {"family": "svm", "C": 0.1, "kernel": "linear", "probability": False,
              "random_state": 123, "class_weight": None}
    scaler_inputs = []
    original_fit = runner.StandardScaler.fit

    def scaler_fit(self, values, *args, **kwargs):
        scaler_inputs.append(np.array(values))
        return original_fit(self, values, *args, **kwargs)

    monkeypatch.setattr(runner.StandardScaler, "fit", scaler_fit)
    model = runner.fit_model(params, x, y, groups, inner)
    assert isinstance(model, CalibratedClassifierCV) and model.ensemble is False
    fitted = model.calibrated_classifiers_[0].estimator
    assert list(fitted.named_steps) == ["imputer", "scaler", "classifier"]
    assert fitted.named_steps["scaler"].n_samples_seen_ == len(known)
    assert sorted(len(values) for values in scaler_inputs) == [12, 12, 12, 18]
    for train, _ in inner:
        assert any(np.array_equal(values[:, 8], x[train, 8]) for values in scaler_inputs)
    assert len(runner.checked_scores(model, x)) == len(known)
    with pytest.raises(ValueError, match="no seed fallback"):
        runner.fit_model(params, x, y, groups, None)
    x[:, 0] = np.nan
    with pytest.raises(ValueError, match="All-missing"):
        runner.fit_model(params, x, y, groups, inner)


def test_existing_output_refused_before_read(tmp_path, monkeypatch):
    def forbidden(*args):
        pytest.fail("must not read sources for existing output")

    monkeypatch.setattr(runner, "load_sources", forbidden)
    with pytest.raises(ValueError, match="new"):
        runner.run(tmp_path / "absent", tmp_path / "missing", tmp_path)


@pytest.fixture
def fake_experiment(tmp_path, monkeypatch):
    """Only test patches bypass strict source SHA/runtime gates; runtime has no fixture flag."""
    from app.ml import owner_pending_synthetic as generator

    dev, snapshot, output = [tmp_path / n for n in ("dev", "snapshot", "output")]
    dev.mkdir()
    snapshot.mkdir()
    known, study, plan = fixture_rows()
    world = {"rows": study}
    final = {"rows": [{**r, "client_id": r["client_id"].replace("UNIT77", "UNIT123"),
                       "loan_id": r["loan_id"].replace("UNIT77", "UNIT123"),
                       "replica_id": "UNIT123", "tenure_days": 999} for r in study]}
    protocol = {"feature_names": runner.FEATURE_NAMES, "runtime": runner.freeze.RUNTIME,
                "tree": {"max_depth": [2, 3, 4], "min_samples_leaf": [8, 16],
                         "class_weight": [None, "balanced"], "random_state": 123},
                "svm": {"C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"],
                        "kernel": "linear", "probability": False, "random_state": 123},
                "thresholds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
                "review_policy": {"daily_cap": 5, "minutes_per_case": 2},
                "cv": {"selection_optimism": "fixture optimistic"},
                "final_replica": {"seed": 123, "prefix": "UNIT123"},
                "illustrative_input": {"features": features()}, "limits": ["fixture only"]}
    for name, value in {
        runner.freeze.MODEL_PROTOCOL: protocol,
        "APF3_PENDING_V6_DATA_PROTOCOL.json": {"simulation": {}},
        "APF3_OWNER_ANCHORS_V4.json": {}, "APF3_OWNER_REVIEW_V5.json": {},
        "pliegues-planificados.json": plan, "summaryauditoria-dev-v6.json": {},
        "preparation_plan.json": {"models_authorized": False},
    }.items():
        runner.write_json(snapshot / name, value)
    runner.write_json(dev / "manifest.json", {"files": {}})
    runner.write_json(dev / "development_audits.json", [])
    before, saved = runner.freeze.audit.inventory(dev), runner.freeze.audit.inventory(snapshot)
    monkeypatch.setattr(runner, "load_sources", lambda *_: (
        protocol, plan, known, study, [world], before, saved))
    monkeypatch.setattr(runner, "PROTOCOL_SHA256", runner.freeze.audit.sha(
        snapshot / runner.freeze.MODEL_PROTOCOL))
    monkeypatch.setattr(runner, "validate_runtime", lambda expected: expected)
    monkeypatch.setattr(runner, "interpretation", lambda *_: {"fixture": True})
    real_fit = runner.fit_model

    def fake_fit(params, x, y, groups, inner):
        assert len(y) in (12, 18) and set(y) == {0, 1}
        assert inner is not None and len(inner) == 3
        return real_fit({"family": "constant_1"}, x, y, groups, inner)

    monkeypatch.setattr(runner, "fit_model", fake_fit)
    events, score_calls = [], []
    real_scores = runner.checked_scores

    def score_spy(model, x):
        if np.all(np.asarray(x)[:, 8] == 999):
            score_calls.append((id(model), len(x)))
        return real_scores(model, x)

    monkeypatch.setattr(runner, "checked_scores", score_spy)

    def fake_generator(anchors, simulation, review, data, seed, prefix):
        assert seed == 123 and prefix == "UNIT123"
        runner.verify_freeze(output)
        assert not score_calls
        assert len(runner.load_json(output / "cv_search.json")["candidates"]) == 18
        events.append("generate_after_freeze")
        return final

    monkeypatch.setattr(generator, "generate_owner_pending_dataset", fake_generator)
    monkeypatch.setattr(generator, "validate_owner_pending_dataset", lambda *_: {
        "hard_constraints_pass": True, "adequacy": {"adequate": False},
        "legacy_grant_scale_flag": False})
    # Fake artifacts deliberately contain Dummy rather than tree/SVM; test inference separately.
    monkeypatch.setattr(runner, "predict", lambda *_: {"known_label": None, "fixture": True})
    return dev, snapshot, output, events, score_calls, final


def test_end_to_end_freeze_before_fake_generator_and_one_final_batch(fake_experiment):
    dev, snapshot, output, events, calls, _ = fake_experiment
    before = runner.freeze.audit.inventory(dev)
    report = runner.run(dev, snapshot, output)
    assert events == ["generate_after_freeze"]
    assert len(calls) == len({identity for identity, _ in calls}) == 4
    assert all(n == 19 for _, n in calls)
    assert report["final"]["evaluation_batch_calls_per_model"] == dict.fromkeys(
        (*runner.FAMILIES, *runner.BASELINES), 1)
    assert runner.freeze.audit.inventory(dev) == before
    search = runner.load_json(output / "cv_search.json")
    assert sum(len(c["threshold_results"]) for c in search["candidates"]) == 126
    for candidate in search["candidates"]:
        assert candidate["oof_prediction_counts"] == [1] * 19
        assert len(candidate["oof_probabilities"]) == 19
    final = runner.load_json(output / "final_predictions.json")
    for result in final.values():
        assert result["metrics"]["n"] == 18
        assert len(result["predictions"]) == 19
        assert sum(p["actual"] is None for p in result["predictions"]) == 1
    assert report["final"]["audit"]["adequacy"]["adequate"] is False
    assert report["final"]["audit"]["legacy_grant_scale_flag"] is False
    assert runner.verify_freeze(output)["global_winner"] == report["selection"]["global_winner"]


def test_final_validation_failure_preserved_no_retry(fake_experiment, monkeypatch):
    from app.ml import owner_pending_synthetic as generator

    dev, snapshot, output, events, calls, _ = fake_experiment
    monkeypatch.setattr(generator, "validate_owner_pending_dataset", lambda *_: {
        "hard_constraints_pass": False})
    with pytest.raises(ValueError, match="hard validation"):
        runner.run(dev, snapshot, output)
    assert events == ["generate_after_freeze"] and calls == []
    assert runner.load_json(output / "failure.json")["retry"] is False
    assert (output / "final_transactions.json").exists()
    assert not (output / "final_predictions.json").exists()


def test_damaged_persisted_freeze_prevents_generation(fake_experiment, monkeypatch):
    dev, snapshot, output, events, calls, _ = fake_experiment
    original = runner.verify_freeze

    def corrupt_before_gate(directory):
        (directory / "selected_model.joblib").write_bytes(b"corrupt-before-final")
        return original(directory)

    monkeypatch.setattr(runner, "verify_freeze", corrupt_before_gate)
    with pytest.raises(ValueError, match="SHA256"):
        runner.run(dev, snapshot, output)
    assert events == calls == []
    assert not (output / "final_transactions.json").exists()


def test_corrupt_sha_before_deserialization(fake_experiment, monkeypatch):
    dev, snapshot, output, _, _, _ = fake_experiment
    runner.run(dev, snapshot, output)
    (output / "selected_model.joblib").write_bytes(b"corrupt")

    def forbidden(*args):
        pytest.fail("joblib.load must not run with corrupt evidence")

    monkeypatch.setattr(runner.joblib, "load", forbidden)
    with pytest.raises(ValueError, match="SHA256"):
        PREDICT(output, features())


def test_feature_order_mismatch_rejected_before_load(fake_experiment):
    dev, snapshot, output, _, _, _ = fake_experiment
    runner.run(dev, snapshot, output)
    selection = runner.load_json(output / "frozen_selection.json")
    selection["feature_names"] = selection["feature_names"][::-1]
    # Rebuild hashes to ensure this exercises schema checking, not merely byte corruption.
    (output / "frozen_selection.json").unlink()
    runner.write_json(output / "frozen_selection.json", selection)
    manifest = runner.hashes(
        output, runner.MODEL_FILES + ["frozen_selection.json", "protocol.json"])
    (output / "artifact_manifest.json").unlink()
    runner.write_json(output / "artifact_manifest.json", manifest)
    frozen = runner.load_json(output / "freeze_before_final.json")
    frozen["files"] = runner.hashes(output, frozen["files"])
    (output / "freeze_before_final.json").unlink()
    runner.write_json(output / "freeze_before_final.json", frozen)
    with pytest.raises(ValueError, match="feature order"):
        runner.verify_freeze(output)


def test_runtime_pin_checked_without_fitting(monkeypatch):
    monkeypatch.setattr(runner.platform, "python_version", lambda: "0.0")
    with pytest.raises(ValueError, match="runtime mismatch"):
        runner.validate_runtime(runner.freeze.RUNTIME)


def reseal_fixture(output):
    selection = runner.load_json(output / "frozen_selection.json")
    selection["decision_sha256"] = runner.hashes(output, selection["decision_sha256"])
    (output / "frozen_selection.json").unlink()
    runner.write_json(output / "frozen_selection.json", selection)
    manifest = runner.hashes(
        output, runner.MODEL_FILES + ["frozen_selection.json", "protocol.json"])
    (output / "artifact_manifest.json").unlink()
    runner.write_json(output / "artifact_manifest.json", manifest)
    frozen = runner.load_json(output / "freeze_before_final.json")
    frozen["files"] = runner.hashes(output, frozen["files"])
    (output / "freeze_before_final.json").unlink()
    runner.write_json(output / "freeze_before_final.json", frozen)


def test_inference_real_fixture_artifact_and_null_imputation(fake_experiment):
    dev, snapshot, output, _, _, _ = fake_experiment
    report = runner.run(dev, snapshot, output)
    choice = report["selection"]["global_winner"]
    assert choice["family"] == "tree"
    known, _, plan = fixture_rows()
    x, y = runner.matrix(known)
    groups = np.asarray([r["client_id"] for r in known])
    inner = runner.local_inner(plan["inner_sigmoid_full_train"], range(len(known)), known)
    model = FIT(choice["params"], x, y, groups, inner)
    runner.joblib.dump(model, output / "tree.joblib")
    (output / "selected_model.joblib").write_bytes((output / "tree.joblib").read_bytes())
    reseal_fixture(output)
    result = PREDICT(output, {"features": {**features(), "tenure_days": None}})
    assert result["version"] == runner.VERSION
    assert result["known_label"] is None
    assert result["review_policy_applied"] is result["business_approval"] is False
    assert result["research_only"] is result["illustrative_only"] is True
    assert 0 <= result["probability"] <= 1
    assert result["feature_names"] == runner.FEATURE_NAMES
    assert set(result) == {"version", "origen", "illustrative_only", "known_label", "family",
                           "feature_names", "features", "probability", "threshold", "predicted",
                           "research_only", "business_approval", "review_policy_applied",
                           "review_policy_note"}


def test_wrong_model_family_rejected_even_with_consistent_hashes(fake_experiment):
    dev, snapshot, output, _, _, _ = fake_experiment
    runner.run(dev, snapshot, output)
    with pytest.raises(ValueError, match="family/parameters"):
        PREDICT(output, features())


def test_cli_modes_exclusive_and_no_execution(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "run", lambda *_: pytest.fail("unexpected experiment"))
    for args in (["--development-dir", str(tmp_path)],
                 ["--predict-artifact-dir", str(tmp_path)],
                 ["--development-dir", str(tmp_path), "--protocol-dir", str(tmp_path),
                  "--output-dir", str(tmp_path), "--input-json", "input.json"]):
        with pytest.raises(SystemExit):
            runner.main(args)


def test_duplicate_illustration_omitted_without_predict(fake_experiment, monkeypatch):
    dev, snapshot, output, _, _, final = fake_experiment
    final["rows"][0].update(features())
    monkeypatch.setattr(runner, "predict", lambda *_: pytest.fail("duplicate must not be scored"))
    report = runner.run(dev, snapshot, output)
    assert report["illustrative_inference"]["status"] == "omitted_duplicate"
