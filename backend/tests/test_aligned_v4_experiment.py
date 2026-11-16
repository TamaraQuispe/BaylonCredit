"""Tiny fixtures only. The actual owner-aligned generator is never called here."""

import copy
import csv
import json
import sys
import types
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.calibration import CalibratedClassifierCV

from scripts import academic_credit_aligned_v4 as cv

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_SEEDS = (-101, -102, -103)


@pytest.fixture
def sources():
    return (
        (FIXTURES / "APF3_OWNER_ANCHORS_V4.json").read_bytes(),
        (FIXTURES / "APF3_ALIGNED_V4_PROTOCOL.json").read_bytes(),
    )


@pytest.fixture
def protocol(sources):
    return json.loads(sources[1])


def world_fixture(prefix="FIX", clients=6):
    rows = []
    for client in range(clients):
        for number, label in enumerate((0, 1, 0, 1, None)):
            row = dict.fromkeys(cv.FEATURE_NAMES, 0)
            row.update(
                {
                    "completed_sales": number + 1,
                    "paid_credits": number,
                    "paid_late": number // 2,
                    "requested_ratio": 0.25,
                    "tenure_days": 30 + client,
                    "punctuality_rate": 0.5,
                    "loan_id": f"{prefix}-L{client:02}-{number}",
                    "client_id": f"{prefix}-C{client:02}",
                    "replica_id": prefix,
                    "evaluated_at": "2001-01-02T10:00:00",
                    "phase": "study",
                    "late_payment": label,
                    "origen": "simulado",
                }
            )
            rows.append(row)
    rows.append({**rows[0], "loan_id": f"{prefix}-WARMUP", "phase": "warmup"})
    return {"rows": rows, "origen": "simulado"}


def audit_fixture():
    return {
        "hard_constraints_pass": True,
        "grant_scale_pass": True,
        "mean_weekly_study_grants": 12,
        "mean_weekly_study_grant_clients": 9,
        "mean_weekly_study_attempts": 12,
        "fixture_only": True,
    }


def test_frozen_sources_grid_and_old_form_excluded(sources, protocol):
    cv.validate_sources(*sources)
    anchors = json.loads(sources[0])
    assert "Rildo" in anchors["authoritative_form"]
    assert "excluded" in anchors["source_policy"]
    assert anchors["not_a_training_dataset"]
    assert protocol["selection"]["minimum_precision"] is None
    assert len(cv.candidate_grid(protocol)) == 18
    assert len(protocol["thresholds"]) == 7
    assert len(protocol["development_replicas"]) == 2
    assert protocol["illustrative_input"]["requested_ratio"] * anchors["client_cap_pen"] == 20
    with pytest.raises(ValueError, match="Rildo"):
        cv.validate_sources(b'{"source": "previous hypothetical owner"}', sources[1])
    with pytest.raises(ValueError, match="protocol SHA256"):
        cv.validate_sources(sources[0], sources[1] + b" ")


def test_small_group_fallback_and_stop():
    rows = cv.study_rows(world_fixture(clients=2))
    rows = [r for r in rows if r["late_payment"] is not None]
    x, y = cv.matrix(rows)
    groups = np.asarray([r["client_id"] for r in rows])
    splits = cv.grouped_splits(x, y, groups, 20261122)
    assert len(splits) == 2
    coverage = np.zeros(len(rows), dtype=int)
    for train, valid in splits:
        assert not set(groups[train]) & set(groups[valid])
        coverage[valid] += 1
    assert np.all(coverage == 1)
    with pytest.raises(ValueError, match="Neither 3 nor 2"):
        cv.grouped_splits(x[:4], y[:4], groups[:4], 20261122)
    with pytest.raises(ValueError, match="Neither 3 nor 2"):
        cv.grouped_splits(x, np.zeros_like(y), groups, 20261122)


def test_real_nested_grouped_svm_and_training_only_preprocessing(protocol, monkeypatch):
    rows = [r for r in cv.study_rows(world_fixture(clients=12)) if r["late_payment"] is not None]
    x, y = cv.matrix(rows)
    groups = np.asarray([r["client_id"] for r in rows])
    outer = cv.grouped_splits(x, y, groups, 20261122)
    train, valid = outer[0]
    x[valid] = 1e10
    x[train[0], 0] = np.nan
    inner = cv.grouped_splits(x[train], y[train], groups[train], 20261123)
    fitted_matrices = []
    original_fit = cv.SimpleImputer.fit

    def spy(self, values, *args, **kwargs):
        fitted_matrices.append(np.asarray(values).copy())
        return original_fit(self, values, *args, **kwargs)

    monkeypatch.setattr(cv.SimpleImputer, "fit", spy)
    model = cv.fit_model(cv.candidate_grid(protocol)[12], x[train], y[train], groups[train], inner)
    assert isinstance(model, CalibratedClassifierCV)
    assert model.method == "sigmoid" and model.ensemble is False
    assert model.estimator.named_steps["classifier"].probability is False
    assert len(fitted_matrices) == len(inner) + 1
    for i, (it, iv) in enumerate(inner):
        assert not set(groups[train][it]) & set(groups[train][iv])
        assert not set(groups[train][it]) & set(groups[valid])
        np.testing.assert_allclose(fitted_matrices[i], x[train][it], equal_nan=True)
    assert all(np.nanmax(values) < 1e10 for values in fitted_matrices)
    fitted = model.calibrated_classifiers_[0].estimator
    np.testing.assert_allclose(
        fitted.named_steps["imputer"].statistics_, np.nanmedian(x[train], axis=0)
    )
    before = fitted.named_steps["scaler"].mean_.copy()
    assert np.isfinite(cv.positive_scores(model, x[valid])).all()
    np.testing.assert_array_equal(before, fitted.named_steps["scaler"].mean_)
    assert "margin" in cv.interpretation(model, "svm")["caveat"]
    assert len(cv.interpretation(model, "svm")["standardized_coefficients"]) == 11


def test_tree_same_pipeline_raw_rules_no_mutation(protocol):
    rows = [r for r in cv.study_rows(world_fixture()) if r["late_payment"] is not None]
    x, y = cv.matrix(rows)
    x[:, 0] *= 100
    model = cv.fit_model({"family": "tree", "max_depth": 2, "random_state": 42}, x, y, None)
    assert list(model.named_steps) == ["imputer", "scaler", "classifier"]
    thresholds = model.named_steps["classifier"].tree_.threshold.copy()
    value = cv.interpretation(model, "tree")
    np.testing.assert_array_equal(thresholds, model.named_steps["classifier"].tree_.threshold)
    assert "completed_sales" in value["raw_unit_rules"]


@pytest.mark.parametrize(("family", "probability"), [("most_frequent", 0), ("constant_1", 1)])
def test_real_reference_pipelines(family, probability):
    rows = [r for r in cv.study_rows(world_fixture()) if r["late_payment"] is not None]
    x, y = cv.matrix(rows)
    model = cv.fit_model({"family": family}, x, y, None)
    assert list(model.named_steps) == ["imputer", "scaler", "classifier"]
    np.testing.assert_array_equal(cv.positive_scores(model, x), np.full(len(y), probability))


def test_policy_per_replica_cap_ties_unknowns_and_own_metrics(protocol):
    base = cv.study_rows(world_fixture())[0]
    rows = [
        {
            **base,
            "replica_id": replica,
            "loan_id": f"{replica}-{i}",
            "late_payment": None if i == 0 else int(i in (1, 5)),
        }
        for replica in ("A", "B")
        for i in range(7)
    ]
    scores = np.full(len(rows), 0.9)
    result = cv.evaluate_cached(rows, scores, 0.5, protocol["review_policy"], True)
    policy = result["review_policy"]
    assert policy["reviews"] == 10 and policy["daily_max"] == 5
    assert policy["reviews_unknown"] == 2 and policy["reviews_known"] == 8
    assert policy["days_over_before_cap"] == 2 and policy["minutes_hypothetical"] == 20
    assert policy["per_replica"]["A"]["reviews"] == policy["per_replica"]["B"]["reviews"] == 5
    assert all(p["review"] == int(int(p["loan_id"][-1]) < 5) for p in result["predictions"])
    assert policy["metrics"]["confusion_matrix"] == [[2, 6], [2, 2]]
    assert policy["metrics"]["precision"] == 0.25
    assert policy["metrics"]["recall"] == 0.5
    assert policy["metrics"]["f2"] == pytest.approx(10 / 24)
    assert result["metrics"]["n"] == 12 and result["metrics"]["recall"] == 1
    assert result["metrics"]["precision"] == pytest.approx(1 / 3)
    assert "roc_auc" not in policy["metrics"] and "brier" not in policy["metrics"]
    assert all(p["actual"] is None for p in result["predictions"] if p["loan_id"].endswith("-0"))
    # UTC midnight belongs to the previous Lima civil day.
    rows[0]["evaluated_at"] = "2001-01-03T01:00:00+00:00"
    _, unchanged = cv.review_policy(rows, scores, 0.5, protocol["review_policy"])
    assert len(unchanged["daily"]) == 2


def test_policy_threshold_then_descending_score_before_loan_id(protocol):
    rows = cv.study_rows(world_fixture(clients=2))
    scores = np.asarray([0.5, 0.4, 0.9, 0.8, 0.7, 0.6, 0.65, 0.2, 0.1, 0.05])
    actions, policy = cv.review_policy(rows, scores, 0.5, protocol["review_policy"])
    assert actions.tolist() == [0, 0, 1, 1, 1, 1, 1, 0, 0, 0]
    # Six above threshold: the lowest eligible score is dropped, not the last loan ID.
    assert policy["days_over_before_cap"] == 1


def selection_entry(index=0, threshold=0.5, **changes):
    value = {"f2": 0.8, "recall": 0.8, "precision": 0.3, "f1": 0.4}
    value.update(changes)
    return {
        "family": "tree",
        "candidate_index": index,
        "threshold": threshold,
        "review_policy": {"metrics": value, "reviews": 10},
    }


def test_selection_no_old_precision_floor_and_metric_priority():
    best = selection_entry(f2=0.95, precision=0.1)
    other = selection_entry(index=1, f2=0.9, precision=0.99)
    assert cv.select_candidate([other, best])["candidate_index"] == 0
    for field in ("recall", "precision", "f1"):
        improved = selection_entry(index=1, **{field: 0.99})
        assert cv.select_candidate([selection_entry(), improved])["candidate_index"] == 1
    # Recall dominates precision, and precision dominates F1.
    assert (
        cv.select_candidate([selection_entry(recall=0.9), selection_entry(index=1, precision=1)])[
            "candidate_index"
        ]
        == 0
    )
    assert (
        cv.select_candidate([selection_entry(precision=0.9), selection_entry(index=1, f1=1)])[
            "candidate_index"
        ]
        == 0
    )


def test_selection_fewer_reviews_candidate_order_then_threshold():
    fewer = selection_entry(index=2)
    fewer["review_policy"]["reviews"] = 9
    assert cv.select_candidate([selection_entry(), fewer])["candidate_index"] == 2
    assert (
        cv.select_candidate([selection_entry(index=1), selection_entry(threshold=0.1)])[
            "candidate_index"
        ]
        == 0
    )
    assert (
        cv.select_candidate([selection_entry(threshold=0.4), selection_entry()])["threshold"] == 0.5
    )


def test_unresolved_only_final_has_no_invented_metrics(protocol):
    rows = [{**r, "late_payment": None} for r in cv.study_rows(world_fixture())]
    result = cv.evaluate_cached(rows, np.ones(len(rows)), 0.5, protocol["review_policy"], True)
    assert result["metrics"]["n"] == 0 and result["metrics"]["f2"] is None
    assert result["review_policy"]["reviews_unknown"] == 5
    assert result["error_count"] == 0


@pytest.mark.parametrize(
    "bad",
    [
        "hard_constraints_pass",
        "grant_scale_pass",
        "mean_weekly_study_grants",
        "mean_weekly_study_grant_clients",
    ],
)
def test_source_scale_gate(bad, protocol):
    audit = audit_fixture()
    assert cv.source_audit_pass(audit, protocol)
    audit[bad] = False if bad.endswith("pass") else 0
    assert not cv.source_audit_pass(audit, protocol)


@pytest.fixture
def mocked_run(tmp_path, sources, protocol, monkeypatch):
    """Replace the import itself, so no actual generator can run, even by accident."""
    anchors_path, protocol_path = tmp_path / "anchors.json", tmp_path / "protocol.json"
    with anchors_path.open("xb") as file:
        file.write(sources[0])
    for spec, seed in zip(protocol["development_replicas"], FIXTURE_SEEDS[:2], strict=True):
        spec["seed"] = seed
    protocol["final_replica"]["seed"] = FIXTURE_SEEDS[2]
    cv.write_json(protocol_path, protocol)
    output = tmp_path / "out"
    state = {
        "generated": [],
        "fits": [],
        "final_batches": [],
        "bad_development": False,
        "bad_final_physical": False,
        "duplicate_example": False,
    }
    real_fit, real_interpretation = cv.fit_model, cv.interpretation

    def fixture_sources(calibration_bytes, protocol_bytes):
        assert calibration_bytes == sources[0]
        parsed = json.loads(protocol_bytes)
        assert [s["seed"] for s in parsed["development_replicas"]] == list(FIXTURE_SEEDS[:2])
        assert parsed["final_replica"]["seed"] == FIXTURE_SEEDS[2]

    def fit(params, x, y, groups, inner=None):
        assert FIXTURE_SEEDS[2] not in state["generated"], "No fit after final generation"
        assert np.all(y != None)  # noqa: E711
        state["fits"].append(params)
        # Deliberately weak cheap surrogate. Real grouped SVM is tested separately above.
        model = real_fit(
            {"family": "tree", "min_samples_leaf": 1000, "random_state": 42}, x, y, groups
        )
        original_predict = model.predict_proba

        def batch(values):
            if FIXTURE_SEEDS[2] in state["generated"]:
                state["final_batches"].append((id(model), len(values)))
            return original_predict(values)

        monkeypatch.setattr(model, "predict_proba", batch)
        return model

    def generate(anchors, simulation, seed, prefix):
        assert seed in FIXTURE_SEEDS, "Real study seeds must NEVER be used by these tests"
        assert seed not in state["generated"]
        assert (output / "calibration.json").read_bytes() == sources[0]
        assert (output / "protocol.json").read_bytes() == protocol_path.read_bytes()
        provenance = json.loads((output / "provenance.json").read_bytes())
        assert provenance["source_anchors"] == anchors
        assert provenance["source_anchors_dict_sha256"] == cv.digest(anchors)
        assert all(provenance["code_sha256"].values())
        assert simulation == protocol["simulation"]
        if seed == FIXTURE_SEEDS[2]:
            assert state["generated"] == list(FIXTURE_SEEDS[:2])
            frozen = json.loads((output / "frozen_selection.json").read_bytes())
            for name, value in frozen["decision_sha256"].items():
                assert cv.sha256((output / name).read_bytes()) == value
            search = json.loads((output / "cv_search.json").read_bytes())
            assert len(search["candidates"]) == 18
            assert sum(len(c["threshold_results"]) for c in search["candidates"]) == 126
            assert all(
                all(count == 1 for count in c["oof_prediction_counts"])
                for c in search["candidates"]
            )
            manifest = json.loads((output / "artifact_manifest.json").read_bytes())
            assert len(manifest) == 6
            for name, value in manifest.items():
                assert cv.sha256((output / name).read_bytes()) == value
        state["generated"].append(seed)
        world = world_fixture(prefix)
        if state["duplicate_example"]:
            world["rows"][0].update(protocol["illustrative_input"])
        return world

    def validate(world, anchors, simulation):
        if len(state["generated"]) == 3 and state["bad_final_physical"]:
            raise AssertionError("fixture physical violation")
        audit = audit_fixture()
        if len(state["generated"]) == 3 or state["bad_development"]:
            # Final failure must remain visible, without aborting the report or regenerating.
            audit["grant_scale_pass"] = False
        return audit

    module = types.ModuleType("app.ml.owner_aligned_synthetic")
    module.generate_owner_aligned_dataset = generate
    module.validate_owner_aligned_dataset = validate
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(cv, "validate_sources", fixture_sources)
    monkeypatch.setattr(cv, "fit_model", fit)
    monkeypatch.setattr(cv, "interpretation", lambda m, f: real_interpretation(m, "tree"))
    # Do not serialize local instrumentation; preserve the actual fitted pipeline instead.
    original_dump = cv.joblib.dump

    def dump(model, path):
        saved = model.__dict__.pop("predict_proba", None)
        try:
            return original_dump(model, path)
        finally:
            if saved is not None:
                model.__dict__["predict_proba"] = saved

    monkeypatch.setattr(cv.joblib, "dump", dump)
    return anchors_path, protocol_path, output, state


def test_end_to_end_mocked_freeze_final_cache_and_inference(mocked_run, monkeypatch, tmp_path):
    anchors, protocol, output, state = mocked_run
    report = cv.run(anchors, protocol, output)
    assert state["generated"] == list(FIXTURE_SEEDS)
    assert len(state["fits"]) == 18 * 3 + 2 * 3 + 4
    assert len(state["final_batches"]) == 4
    assert len({model for model, _ in state["final_batches"]}) == 4
    assert all(size == 30 for _, size in state["final_batches"])
    assert set(report["models"]) == {"tree", "svm", *cv.BASELINES}
    assert not report["final"]["source_alignment_pass"]
    assert report["development"]["resolved_study_rows"] == 48
    assert report["development"]["unknown_study_rows"] == 12
    assert report["final"]["known_rows"] == 24
    folds = json.loads((output / "fold_audit.json").read_bytes())
    for outer in folds["outer"]:
        assert outer["client_disjoint"]
        assert not set(outer["train_client_ids"]) & set(outer["validation_client_ids"])
    for parent in folds["svm_outer_training_calibration"]:
        outer = folds["outer"][parent["outer_fold"]]
        for inner in parent["folds"]:
            assert inner["client_disjoint"]
            assert set(inner["train_indices"]) <= set(outer["train_indices"])
            assert set(inner["validation_indices"]) <= set(outer["train_indices"])
    assert all(fold["client_disjoint"] for fold in folds["svm_full_development_calibration"])
    assert report["baseline_comparison"]["final"]["failure"]
    assert not report["baseline_comparison"]["final"]["proposed_ml_f2_improves_both"]
    for name, item in report["models"].items():
        for split in ("train", "oof", "final"):
            assert "brier" in item[split] and "confusion_matrix" in item[split]
            assert "brier" not in item["review_policy"][split]["metrics"]
        assert item["threshold"] == (
            0.5 if name in cv.BASELINES else report["selection"]["families"][name]["threshold"]
        )
        assert len(item["error_cases"]) >= 3
        assert all(case["actual"] is not None for case in item["error_cases"])
    saved = json.loads((output / "final_predictions.json").read_bytes())
    assert all(len(result["predictions"]) == 30 for result in saved.values())
    assert all(sum(p["actual"] is None for p in r["predictions"]) == 6 for r in saved.values())
    for filename, label in (
        ("development_rows.csv", "late_payment"),
        ("final_rows.csv", "late_payment"),
        ("final_predictions.csv", "actual"),
    ):
        with (output / filename).open() as file:
            rows = list(csv.DictReader(file))
        assert any(row[label] == "" for row in rows)
        assert all(row["origen"] == "simulado" for row in rows)
    assert json.loads((output / "aligned_v4_report.json").read_bytes()) == report
    assert report["illustrative_inference"]["requested_amount_pen"] == 20
    assert report["illustrative_inference"]["known_label"] is None
    assert report["illustrative_inference"]["distinctness_pass"]
    model = joblib.load(output / "selected_model.joblib")
    assert list(model.named_steps) == ["imputer", "scaler", "classifier"]
    monkeypatch.setattr(cv, "fit_model", lambda *a: pytest.fail("Inference attempted fitting"))
    result_path = tmp_path / "inference.json"
    cv.main(
        [
            "--predict-artifact-dir",
            str(output),
            "--input-json",
            str(output / "illustrative_input.json"),
            "--output-json",
            str(result_path),
        ]
    )
    assert (
        json.loads(result_path.read_bytes())["probability"]
        == report["illustrative_inference"]["probability"]
    )
    with pytest.raises(SystemExit):
        cv.main(
            [
                "--predict-artifact-dir",
                str(output),
                "--input-json",
                str(output / "illustrative_input.json"),
                "--output-json",
                str(result_path),
            ]
        )
    with pytest.raises(ValueError, match="never reuse"):
        cv.run(anchors, protocol, output)


def test_development_failure_blocks_all_fitting_and_final(mocked_run):
    anchors, protocol, output, state = mocked_run
    state["bad_development"] = True
    with pytest.raises(ValueError, match="Development physical/grant"):
        cv.run(anchors, protocol, output)
    assert state["fits"] == [] and state["generated"] == list(FIXTURE_SEEDS[:2])
    assert (output / "development_audits.json").exists()
    assert not (output / "frozen_selection.json").exists()


def test_duplicate_illustration_reported_never_replaced(mocked_run):
    anchors, protocol, output, state = mocked_run
    state["duplicate_example"] = True
    report = cv.run(anchors, protocol, output)
    assert not report["illustrative_inference"]["distinctness_pass"]
    assert "not replaced" in report["illustrative_inference"]["failure"]
    assert (
        json.loads((output / "illustrative_input.json").read_bytes())["features"]
        == json.loads(protocol.read_bytes())["illustrative_input"]
    )
    assert len(state["final_batches"]) == 4


def test_final_physical_audit_exception_preserves_report_without_retry(mocked_run):
    anchors, protocol, output, state = mocked_run
    state["bad_final_physical"] = True
    report = cv.run(anchors, protocol, output)
    assert not report["final"]["source_alignment_pass"]
    assert "fixture physical violation" in report["final"]["audit"]["validator_error"]
    assert state["generated"] == list(FIXTURE_SEEDS)
    assert (output / "aligned_v4_report.json").exists()


def test_baseline_comparison_strict_both_and_capacity():
    models = {
        name: {
            "review_policy": {
                split: {"metrics": {"f2": value}, "capacity_respected": True}
                for split in ("train", "oof", "final")
            }
        }
        for name, value in (("tree", 0.8), ("most_frequent", 0.1), ("constant_1", 0.8))
    }
    assert not cv.baseline_comparison(models, "tree")["final"]["proposal_pass"]
    models["tree"]["review_policy"]["final"]["metrics"]["f2"] = 0.9
    assert cv.baseline_comparison(models, "tree")["final"]["proposal_pass"]
    models["tree"]["review_policy"]["final"]["capacity_respected"] = False
    assert not cv.baseline_comparison(models, "tree")["final"]["proposal_pass"]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("completed_sales", True),
        ("paid_credits", "3"),
        ("outstanding", -1),
        ("outstanding", float("inf")),
        ("outstanding", float("nan")),
        ("completed_sales", 1.5),
        ("tenure_days", 0.5),
        ("requested_ratio", 0),
        ("requested_ratio", 1.1),
        ("utilization", 1.1),
        ("punctuality_rate", 1.1),
        ("overdue_rate", 1.1),
        ("paid_late", 5),
    ],
)
def test_invalid_inference_input_before_unpickle(tmp_path, protocol, monkeypatch, name, value):
    features = copy.deepcopy(protocol["illustrative_input"])
    features[name] = value
    monkeypatch.setattr(cv.joblib, "load", lambda *a: pytest.fail("Invalid input was unpickled"))
    with pytest.raises(ValueError):
        cv.predict(tmp_path, {"features": features})


def inference_artifact(tmp_path, protocol, feature_names=None):
    rows = [r for r in cv.study_rows(world_fixture()) if r["late_payment"] is not None]
    x, y = cv.matrix(rows)
    model = cv.fit_model({"family": "constant_1"}, x, y, None)
    joblib.dump(model, tmp_path / "selected_model.joblib")
    cv.write_json(
        tmp_path / "frozen_selection.json",
        {
            "version": "academic-owner-aligned-v4",
            "feature_names": cv.FEATURE_NAMES if feature_names is None else feature_names,
            "global_winner": {"family": "tree", "threshold": 0.5},
        },
    )
    cv.write_json(
        tmp_path / "artifact_manifest.json",
        {
            name: cv.sha256((tmp_path / name).read_bytes())
            for name in ("selected_model.joblib", "frozen_selection.json")
        },
    )


@pytest.mark.parametrize("filename", ["selected_model.joblib", "frozen_selection.json"])
def test_hashes_verified_before_unpickle(tmp_path, protocol, monkeypatch, filename):
    inference_artifact(tmp_path, protocol)
    # Deliberate corruption, not an experiment evidence rewrite.
    with (tmp_path / filename).open("ab") as file:
        file.write(b"tampered")
    monkeypatch.setattr(cv.joblib, "load", lambda *a: pytest.fail("Bad hash reached unpickle"))
    with pytest.raises(ValueError, match="SHA256"):
        cv.predict(tmp_path, {"features": protocol["illustrative_input"]})


def test_inference_null_imputation_and_schema(tmp_path, protocol):
    inference_artifact(tmp_path, protocol)
    features = {**protocol["illustrative_input"], "outstanding": None}
    result = cv.predict(tmp_path, {"features": features})
    assert result["known_label"] is None and result["business_approval"] is False
    assert result["probability"] == 1
    for data in ({"features": {"late_payment": 1}}, {"features": features, "late_payment": 1}):
        with pytest.raises(ValueError):
            cv.predict(tmp_path, data)


def test_artifact_feature_order_checked_before_unpickle(tmp_path, protocol, monkeypatch):
    inference_artifact(tmp_path, protocol, list(reversed(cv.FEATURE_NAMES)))
    monkeypatch.setattr(cv.joblib, "load", lambda *a: pytest.fail("Bad schema reached unpickle"))
    with pytest.raises(ValueError, match="schema/version"):
        cv.predict(tmp_path, protocol["illustrative_input"])


def test_output_immutable_and_cli_modes(tmp_path):
    output = cv.prepare_output(tmp_path / "new")
    cv.write_json(output / "evidence.json", {"preserve": True})
    with pytest.raises(ValueError, match="never reuse"):
        cv.prepare_output(output)
    with pytest.raises(FileExistsError):
        cv.write_json(output / "evidence.json", {})
    with pytest.raises(ValueError, match="production app"):
        cv.prepare_output(cv.BACKEND / "app" / "forbidden-output")
    with pytest.raises(SystemExit):
        cv.main(["--predict-artifact-dir", str(output), "--calibration", "x"])
    with pytest.raises(SystemExit):
        cv.main(["--protocol", "x", "--output-dir", "x"])


def test_oof_coverage_guard(protocol, monkeypatch):
    rows = [r for r in cv.study_rows(world_fixture()) if r["late_payment"] is not None]
    x, y = cv.matrix(rows)
    groups = np.asarray([r["client_id"] for r in rows])
    splits = cv.grouped_splits(x, y, groups, 20261122)
    inner = [cv.grouped_splits(x[t], y[t], groups[t], 20261123) for t, _ in splits]
    params = cv.candidate_grid(protocol)[0]
    scores, counts = cv.oof_predict(params, x, y, groups, splits, inner)
    assert np.isfinite(scores).all() and np.all(counts == 1)
    with pytest.raises(ValueError, match="exactly once"):
        cv.oof_predict(params, x, y, groups, splits + splits[:1], inner + inner[:1])


def test_no_old_runner_validator_or_model_factory_import():
    import ast

    tree = ast.parse(Path(cv.__file__).read_text())
    imported = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "scripts.academic_credit_grouped_cv"
        for alias in node.names
    ]
    assert set(imported) == {
        "FEATURE_NAMES",
        "candidate_grid",
        "fold_audit",
        "interpretation",
        "matrix",
        "metrics",
        "positive_scores",
        "prepare_output",
        "sha256",
        "write_json",
    }
