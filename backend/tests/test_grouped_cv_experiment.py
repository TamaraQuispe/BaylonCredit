"""Small fixtures only: never execute the real APF3 experiment or final generator."""

import copy
import json
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.calibration import CalibratedClassifierCV
from sklearn.exceptions import ConvergenceWarning

from scripts import academic_credit_grouped_cv as cv


@pytest.fixture
def protocol():
    # The source digest is filled from a tiny fixture, never the real development ledger.
    return {
        "version": "academic-grouped-cv-v3",
        "target": "late_payment",
        "development_source_sha256": "fixture",
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
        "selection": {
            "metric": "F2",
            "beta": 2,
            "minimum_precision": 0.5,
            "tie_breakers": [
                "recall",
                "f1",
                "precision",
                "Earlier candidate in declared grid",
                "Threshold nearest 0.5",
            ],
            "oof_limit": "OOF used for search; optimistic, not an unbiased final estimate",
        },
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
        "limitations": ["Fixture research only"],
    }


def ledger_fixture(n_clients=30):
    clients, rows, loans, sales = [], [], [], []
    for client in range(n_clients):
        client_id = f"FIX-C{client:03d}"
        split = "train" if client < n_clients // 2 else "validation"
        clients.append({"client_id": client_id, "split": split})
        for number in range(4):
            row = dict.fromkeys(cv.FEATURE_NAMES, 0.0)
            row.update(
                {
                    "loan_id": f"FIX-L{client:03d}-{number}",
                    "client_id": client_id,
                    "split": split,
                    "late_payment": number % 2,
                    "scenario": "fixture_late" if number % 2 else "fixture_punctual",
                }
            )
            rows.append(row)
            loans.append({"loan_id": row["loan_id"], "client_id": client_id, "split": split})
        sales.append({"client_id": client_id})
    return {"clients": clients, "rows": rows, "loans": loans, "sales": sales}


def grouped_data():
    rows = ledger_fixture()["rows"]
    x, y = cv.matrix(rows)
    # Give the models nonconstant features, but preserve both labels in every client.
    x[:, 0] = np.arange(len(rows)) % 7
    groups = np.asarray([row["client_id"] for row in rows])
    return x, y, groups


def entry(index=0, threshold=0.5, f2=0.7, precision=0.6, recall=0.8, f1=0.65, family="tree"):
    return {
        "family": family,
        "candidate_index": index,
        "threshold": threshold,
        "params": {"family": family},
        "metrics": {"f2": f2, "precision": precision, "recall": recall, "f1": f1},
    }


def test_protocol_and_declared_grid(protocol):
    cv.validate_protocol(protocol)
    grid = cv.candidate_grid(protocol)
    assert len(grid) == 18
    assert [p["family"] for p in grid] == ["tree"] * 12 + ["svm"] * 6
    assert grid[0] == {
        "family": "tree",
        "max_depth": 2,
        "min_samples_leaf": 8,
        "class_weight": None,
        "random_state": 42,
    }
    assert grid[-1]["C"] == 10 and grid[-1]["class_weight"] == "balanced"
    assert all(p["probability"] is False for p in grid[12:])
    protocol["cv"]["seed"] += 1
    with pytest.raises(ValueError, match="frozen protocol"):
        cv.validate_protocol(protocol)


def test_grouped_folds_and_oof_coverage(protocol):
    x, y, groups = grouped_data()
    splits = cv.grouped_splits(x, y, groups, 5, 20261112)
    coverage = np.zeros(len(y), dtype=int)
    for train, validation in splits:
        assert not set(groups[train]) & set(groups[validation])
        assert not set(train) & set(validation)
        coverage[validation] += 1
    assert np.all(coverage == 1)
    scores, counts = cv.oof_predict(cv.candidate_grid(protocol)[0], x, y, groups, splits)
    assert len(scores) == len(y) and np.isfinite(scores).all()
    assert np.all(counts == 1)
    with pytest.raises(ValueError, match="exactly once"):
        cv.oof_predict(cv.candidate_grid(protocol)[0], x, y, groups, splits + splits[:1])


def test_preprocessing_fits_training_only_with_extreme_heldout(protocol):
    x, y, groups = grouped_data()
    train, validation = cv.grouped_splits(x, y, groups, 5, 20261112)[0]
    x[train[0], 0] = np.nan
    x[validation, :] = 1e12
    model = cv.build_model(cv.candidate_grid(protocol)[0], x[train], y[train], groups[train])
    imputer, scaler = model.named_steps["imputer"], model.named_steps["scaler"]
    expected_medians = np.nanmedian(x[train], axis=0)
    np.testing.assert_allclose(imputer.statistics_, expected_medians)
    np.testing.assert_allclose(scaler.mean_, imputer.transform(x[train]).mean(axis=0))
    before = scaler.mean_.copy()
    cv.positive_scores(model, x[validation])
    np.testing.assert_array_equal(scaler.mean_, before)
    assert np.max(scaler.mean_) < 10


def test_svm_calibration_group_disjoint_and_preprocessing_each_fold(protocol, monkeypatch):
    x, y, groups = grouped_data()
    outer_train, outer_validation = cv.grouped_splits(x, y, groups, 5, 20261112)[0]
    x[outer_validation] = 1e12
    # Capture every imputer fit, including the three calibration folds and final refit.
    fit_matrices = []
    original_fit = cv.SimpleImputer.fit

    def fit_spy(self, values, *args, **kwargs):
        fit_matrices.append(np.asarray(values).copy())
        return original_fit(self, values, *args, **kwargs)

    monkeypatch.setattr(cv.SimpleImputer, "fit", fit_spy)
    model = cv.build_model(
        cv.candidate_grid(protocol)[12], x[outer_train], y[outer_train], groups[outer_train]
    )
    assert isinstance(model, CalibratedClassifierCV)
    assert model.ensemble is False and model.method == "sigmoid"
    assert model.estimator.named_steps["classifier"].probability is False
    assert len(model.cv) == 3 and len(fit_matrices) == 4
    local_groups = groups[outer_train]
    for index, (inner_train, inner_validation) in enumerate(model.cv):
        assert not set(local_groups[inner_train]) & set(local_groups[inner_validation])
        assert not set(local_groups[inner_train]) & set(groups[outer_validation])
        np.testing.assert_array_equal(fit_matrices[index], x[outer_train][inner_train])
    assert all(np.max(values) < 10 for values in fit_matrices)
    fitted = model.calibrated_classifiers_[0].estimator
    np.testing.assert_allclose(fitted.named_steps["scaler"].mean_, x[outer_train].mean(axis=0))
    assert len(cv.interpretation(model, "svm")["standardized_coefficients"]) == 11


def test_selection_precision_guard_and_research_fallback():
    chosen = cv.select_candidate([entry(f2=0.99, precision=0.49), entry(index=1)])
    assert chosen["candidate_index"] == 1 and chosen["feasible"]
    assert not chosen["constraint_failure"] and chosen["research_only"]
    chosen = cv.select_candidate([entry(f2=0.9, precision=0.4), entry(index=1, precision=0.3)])
    assert chosen["candidate_index"] == 0 and not chosen["feasible"]
    assert chosen["constraint_failure"] and chosen["research_only"]
    global_choice = cv.select_candidate(
        [
            entry(f2=0.99, precision=0.4),
            entry(index=12, family="svm", f2=0.6),
        ]
    )
    assert global_choice["family"] == "svm"
    global_fallback = cv.select_candidate(
        [
            cv.select_candidate([entry(f2=0.9, precision=0.4)]),
            cv.select_candidate([entry(index=12, family="svm", f2=0.7, precision=0.3)]),
        ]
    )
    assert global_fallback["family"] == "tree"
    assert global_fallback["constraint_failure"] and not global_fallback["feasible"]


@pytest.mark.parametrize(("field", "higher"), [("recall", 0.9), ("f1", 0.9), ("precision", 0.9)])
def test_selection_metric_tie_breakers(field, higher):
    first, second = entry(), entry(index=1)
    second["metrics"][field] = higher
    assert cv.select_candidate([first, second])["candidate_index"] == 1


def test_selection_declared_candidate_before_nearest_threshold():
    assert cv.select_candidate([entry(index=1), entry(threshold=0.2)])["candidate_index"] == 0
    assert cv.select_candidate([entry(threshold=0.2), entry(threshold=0.5)])["threshold"] == 0.5
    assert cv.select_candidate([entry(threshold=0.4), entry(threshold=0.6)])["threshold"] == 0.4
    # Precision exactly on the frozen floor is feasible.
    assert cv.select_candidate([entry(precision=0.5)])["feasible"]


def test_metrics_f2_and_confusion():
    result = cv.metrics(np.array([0, 0, 1, 1]), [0.1, 0.8, 0.4, 0.9], 0.5)
    assert result["confusion_matrix"] == [[1, 1], [1, 1]]
    assert result["f2"] == 0.5
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    assert result["brier"] == pytest.approx((0.01 + 0.64 + 0.36 + 0.01) / 4)


def test_source_excludes_original_test_and_unlabeled(tmp_path, protocol):
    ledger = ledger_fixture()
    ledger["rows"][0]["late_payment"] = None
    old_test = copy.deepcopy(ledger["rows"][1])
    old_test.update({"client_id": "OLD-TEST", "loan_id": "OLD-TEST-LOAN", "split": "test"})
    # Missing features on the old test ensure it is never made into a matrix.
    for name in cv.FEATURE_NAMES:
        del old_test[name]
    ledger["rows"].append(old_test)
    source = tmp_path / "source.json"
    cv.write_json(source, ledger)
    protocol["development_source_sha256"] = cv.sha256(source.read_bytes())
    _, rows = cv.load_development(source, protocol)
    assert len(rows) == 119
    assert all(row["split"] != "test" and row["late_payment"] is not None for row in rows)
    protocol["development_source_sha256"] = "incorrect"
    with pytest.raises(ValueError, match="SHA256"):
        cv.load_development(source, protocol)


def test_source_rejects_client_crossing_original_splits(tmp_path, protocol):
    ledger = ledger_fixture()
    ledger["rows"][0]["split"] = "test"
    source = tmp_path / "source.json"
    cv.write_json(source, ledger)
    protocol["development_source_sha256"] = cv.sha256(source.read_bytes())
    with pytest.raises(ValueError, match="crosses original"):
        cv.load_development(source, protocol)


def test_output_refuses_reuse_and_production(tmp_path):
    output = cv.prepare_output(tmp_path / "new")
    cv.write_json(output / "evidence.json", {"preserve": True})
    with pytest.raises(ValueError, match="never reuse"):
        cv.prepare_output(output)
    with pytest.raises(ValueError, match="production app"):
        cv.prepare_output(cv.BACKEND / "app" / "do-not-create")
    with pytest.raises(FileExistsError):
        cv.write_json(output / "evidence.json", {})
    assert json.loads((output / "evidence.json").read_text()) == {"preserve": True}


def test_tree_rules_do_not_mutate_saved_pipeline(protocol):
    x, y, groups = grouped_data()
    x[:, 0] = np.arange(len(y)) * 100
    y = (np.arange(len(y)) >= len(y) // 2).astype(int)
    model = cv.build_model(cv.candidate_grid(protocol)[0], x, y, groups)
    thresholds = model.named_steps["classifier"].tree_.threshold.copy()
    rules = cv.interpretation(model, "tree")
    np.testing.assert_array_equal(model.named_steps["classifier"].tree_.threshold, thresholds)
    assert "completed_sales" in rules["raw_unit_rules"]
    classifier = model.named_steps["classifier"]
    feature = classifier.tree_.feature[0]
    assert feature == 0
    scaler = model.named_steps["scaler"]
    expected = thresholds[0] * scaler.scale_[feature] + scaler.mean_[feature]
    assert f"{expected:.6f}" in rules["raw_unit_rules"]


def test_convergence_failure_is_explicit(protocol, monkeypatch):
    import warnings

    def fail(*args, **kwargs):
        warnings.warn("fixture convergence failure", ConvergenceWarning, stacklevel=2)

    monkeypatch.setattr(cv.Pipeline, "fit", fail)
    with pytest.raises(RuntimeError, match="no automatic retuning/reseeding"):
        cv.build_model(cv.candidate_grid(protocol)[0], *grouped_data())


def test_baselines_prevent_unjustified_superiority():
    model_metrics = {
        name: {split: {"f2": 0.7, "precision": 0.6} for split in ("train", "oof", "final")}
        for name in ("tree", *cv.BASELINES)
    }
    result = cv.baseline_comparison(model_metrics, "tree", 0.5)
    assert not result["final"]["selected_superior_to_both"]
    model_metrics["tree"]["final"]["f2"] = 0.9
    model_metrics["constant_1"]["final"]["precision"] = 0.4
    result = cv.baseline_comparison(model_metrics, "tree", 0.5)
    assert not result["final"]["selected_superior_to_both"]


def test_freeze_before_final_small_mocked_factory(tmp_path, protocol, monkeypatch):
    from app.ml import synthetic

    source, protocol_path = tmp_path / "source.json", tmp_path / "protocol.json"
    output = tmp_path / "experiment"
    cv.write_json(source, ledger_fixture())
    protocol["development_source_sha256"] = cv.sha256(source.read_bytes())
    cv.write_json(protocol_path, protocol)
    real_build, real_interpretation = cv.build_model, cv.interpretation
    fit_calls, generated, final_calls = [], [], []

    def factory(params, x, y, groups):
        assert (output / "protocol.json").read_bytes() == protocol_path.read_bytes()
        provenance = json.loads((output / "provenance.json").read_text())
        assert all(provenance[key] for key in ("protocol_sha256", "source_sha256", "code_sha256"))
        assert set(provenance["runtime"]) == {"python", "sklearn", "numpy", "joblib", "scipy"}
        assert not generated, "Nothing may fit after final generation"
        fit_calls.append(params)
        # Cheap stand-in for integration ordering only; real SVM calibration is tested above.
        return real_build({"family": "tree", "max_depth": 2, "random_state": 42}, x, y, groups)

    def generate(n_clients, seed):
        assert (n_clients, seed) == (120, 20261117)
        frozen = json.loads((output / "frozen_selection.json").read_text())
        search = json.loads((output / "cv_search.json").read_text())
        assert len(search["candidates"]) == 18
        assert sum(len(c["threshold_results"]) for c in search["candidates"]) == 126
        assert set(frozen["families"]) == {"tree", "svm"}
        assert frozen["global_winner"]["threshold"] in protocol["thresholds"]
        assert (output / "selected_model.joblib").exists()
        generated.append(True)
        return ledger_fixture(6)

    def validate(ledger):
        for collection in ("clients", "loans", "sales", "rows"):
            assert all(
                row["split"] == "final_test"
                and row["origen"] == "simulado"
                and row["client_id"].startswith("CV3")
                for row in ledger[collection]
            )
        return {"fixture_validated": True}

    evaluate = cv.evaluate_final_once

    def final_spy(model, rows, x, y, threshold):
        assert generated == [True]
        final_calls.append(id(model))
        # Count direct final-matrix calls, not just calls to this wrapper.
        original_predict = model.predict_proba
        predictions = []

        def counted(values):
            predictions.append(len(values))
            return original_predict(values)

        monkeypatch.setattr(model, "predict_proba", counted)
        result = evaluate(model, rows, x, y, threshold)
        assert predictions == [len(rows)]
        return result

    monkeypatch.setattr(cv, "build_model", factory)
    monkeypatch.setattr(
        cv, "interpretation", lambda model, family: real_interpretation(model, "tree")
    )
    monkeypatch.setattr(synthetic, "generate_academic_dataset", generate)
    monkeypatch.setattr(synthetic, "validate_academic_dataset", validate)
    monkeypatch.setattr(cv, "evaluate_final_once", final_spy)
    report = cv.run(source, protocol_path, output)
    assert len(fit_calls) == 18 * 5 + 2 * 5 + 4
    assert len(final_calls) == len(set(final_calls)) == 4
    assert generated == [True]
    assert set(report["models"]) == {"tree", "svm", *cv.BASELINES}
    for name, item in report["models"].items():
        assert all("confusion_matrix" in item[split] for split in ("train", "oof", "final"))
        assert item["threshold"] == (
            0.5 if name in cv.BASELINES else report["selection"]["families"][name]["threshold"]
        )
        assert len(item["error_cases"]) >= 3
        assert set(item["error_cases"][0]["features"]) == set(cv.FEATURE_NAMES)
    assert report["illustrative_inference"]["known_label"] is None
    assert list(report["illustrative_inference"]["features"].values()) == cv.ILLUSTRATIVE_VECTOR
    assert json.loads((output / "grouped_cv_report.json").read_text()) == report
    assert set(report["artifact_sha256"]) == {
        "tree.joblib",
        "svm.joblib",
        "most_frequent.joblib",
        "constant_1.joblib",
        "selected_model.joblib",
    }
    assert "origen" in (output / "final_predictions.csv").read_text().splitlines()[0]
    assert "simulado" in (output / "final_predictions.csv").read_text()
    # Inference must load only; no fitting or generator access is allowed.
    monkeypatch.setattr(cv, "build_model", lambda *args: pytest.fail("Inference attempted fitting"))
    monkeypatch.setattr(
        synthetic,
        "generate_academic_dataset",
        lambda *args: pytest.fail("Inference attempted generation"),
    )
    result_path = tmp_path / "prediction.json"
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
    assert json.loads(result_path.read_text()) == report["illustrative_inference"]
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
    with pytest.raises(ValueError, match="exactly the eleven"):
        cv.predict(output, {"features": {"late_payment": 1}})
    # The packaged artifact is a fitted preprocessing pipeline, not a bare classifier.
    assert list(joblib.load(output / "selected_model.joblib").named_steps) == [
        "imputer",
        "scaler",
        "classifier",
    ]
    for invalid in (True, "3", -1, float("inf")):
        values = dict(zip(cv.FEATURE_NAMES, cv.ILLUSTRATIVE_VECTOR, strict=True))
        values["completed_sales"] = invalid
        with pytest.raises(ValueError, match="finite nonnegative"):
            cv.predict(output, {"features": values})
    (output / "selected_model.joblib").write_bytes(b"tampered")
    monkeypatch.setattr(cv.joblib, "load", lambda *args: pytest.fail("Loaded corrupt artifact"))
    with pytest.raises(ValueError, match="SHA256"):
        cv.predict(
            output, {"features": dict(zip(cv.FEATURE_NAMES, cv.ILLUSTRATIVE_VECTOR, strict=True))}
        )


def test_final_overlap_rejected():
    with pytest.raises(ValueError, match="overlap"):
        cv.rename_final(ledger_fixture(6), {"CV3-C0001"})


def test_script_source_and_schema_are_scoped():
    from app.ml.features import FEATURE_NAMES

    assert cv.FEATURE_NAMES == FEATURE_NAMES and len(FEATURE_NAMES) == 11
    assert Path(cv.__file__).name == "academic_credit_grouped_cv.py"
