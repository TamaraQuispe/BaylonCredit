"""Pure prospective validation tests: no docs mount, models, fitting or generation."""

import csv
from copy import deepcopy

import pytest

from scripts import freeze_pending_v6_model_protocol as freeze


def protocol_template():
    return {
        "frozen_inputs": dict.fromkeys(freeze.FROZEN_KEYS, "a" * 64),
        "stage": "prospective_model_protocol_after_DEV_review_before_any_V6_fit_or_FINAL",
        "current_action": "Freeze protocol and verify inputs only. No V6 fit, final generation, "
                          "artifact promotion, deployment or production change is performed "
                          "in this step.",
        "feature_names": list(freeze.audit.FEATURE_NAMES),
        "feature_policy": {"constant_features": ["pending_overdue", "pending_current",
                                                 "outstanding",
                                                 "utilization", "overdue_rate"]},
        "preprocessing": ["SimpleImputer(strategy=median)", "StandardScaler"],
        "cv": {"group": "client_id", "outer_seed": freeze.audit.OUTER_SEED,
               "inner_seed": freeze.audit.INNER_SEED, "preferred_folds": 3, "fallback_folds": 2,
               "unknown_oof": freeze.UNKNOWN_POLICY, "oof_queue_scope": freeze.QUEUE_SCOPE},
        "tree": {"max_depth": [2, 3, 4], "min_samples_leaf": [8, 16],
                 "class_weight": [None, "balanced"], "random_state": 42},
        "svm": {"kernel": "linear", "C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"],
                "probability": False, "random_state": 42},
        "svm_calibration": {"group": "client_id", "method": "sigmoid", "ensemble": False},
        "thresholds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        "candidate_count": {"tree": 12, "svm": 6, "thresholds_per_candidate": 7,
                            "configuration_threshold_pairs": 126},
        "final_replica": {"seed": 2026111901, "prefix": "PND6-T",
                          "status_at_protocol_freeze": "Not generated or inspected"},
        "runtime": dict(freeze.RUNTIME),
        "review_policy": {"daily_cap": 5, "minutes_per_case": 2},
        "illustrative_input": {"features": dict.fromkeys(freeze.audit.FEATURE_NAMES, 0)},
    }


def test_plain_grid_exact_order_no_estimators():
    protocol = protocol_template()
    with freeze.audit.no_models_or_generation():
        pairs = freeze.validate_protocol(protocol, protocol["frozen_inputs"])
    assert len(pairs) == 126
    assert pairs[0] == (("tree", 2, 8, None), 0.1)
    assert pairs[84] == (("svm", 0.1, None), 0.1)
    assert pairs[-1] == (("svm", 10.0, "balanced"), 0.7)


@pytest.mark.parametrize("mutation", [
    lambda p: p["frozen_inputs"].update(generator_sha256="b" * 64),
    lambda p: p["frozen_inputs"].pop("fold_plan_sha256"),
    lambda p: p["cv"].update(unknown_oof="Drop unknown labels from capacity"),
    lambda p: p["cv"].update(oof_queue_scope="Pool all folds"),
    lambda p: p["final_replica"].update(seed=2026111701),
    lambda p: p["final_replica"].update(prefix="PND6-D1"),
    lambda p: p["feature_names"].append("late_payment"),
    lambda p: p["feature_names"].reverse(),
    lambda p: p["illustrative_input"]["features"].pop("paid_late"),
    lambda p: p["tree"].update(max_depth=[2, 3]),
    lambda p: p["svm"].update(probability=True),
    lambda p: p["thresholds"].append(0.8),
    lambda p: p["candidate_count"].update(configuration_threshold_pairs=127),
    lambda p: p["runtime"].update(sklearn="other"),
    lambda p: p.update(current_action="Train now"),
])
def test_protocol_mutations_rejected(mutation):
    protocol = protocol_template()
    expected = deepcopy(protocol["frozen_inputs"])
    mutation(protocol)
    with pytest.raises(AssertionError):
        freeze.validate_protocol(protocol, expected)


@pytest.mark.parametrize("seed", sorted(freeze.EARLIER_SEEDS))
def test_every_historical_seed_conflicts(seed):
    protocol = protocol_template()
    protocol["final_replica"]["seed"] = seed
    with pytest.raises(AssertionError):
        freeze.validate_protocol(protocol, protocol["frozen_inputs"])


def saved_plan_template():
    # Hand-built partitions, not CV recreation. Each fictional client has both labels.
    known = [{"loan_id": f"L{c}-{y}", "client_id": f"C{c}", "late_payment": y}
             for c in range(6) for y in (0, 1)]
    study = known + [{"loan_id": "U", "client_id": "C0", "late_payment": None}]

    def splits(indices, seed):
        clients = sorted({known[i]["client_id"] for i in indices})
        folds = []
        for number in range(3):
            validation_clients = clients[number::3]
            validation = [i for i in indices if known[i]["client_id"] in validation_clients]
            train = [i for i in indices if i not in validation]
            fold = {"fold": number}
            for side, subset in (("train", train), ("validation", validation)):
                fold.update({side + "_indices": subset,
                             side + "_clients": sorted({known[i]["client_id"] for i in subset}),
                             side + "_size": len(subset),
                             side + "_class_counts": {"0": len(subset) // 2, "1": len(subset) // 2},
                             side + "_minority": len(subset) // 2})
            folds.append(fold)
        return {"n_splits": 3, "seed": seed, "rejected_feasibility": [], "folds": folds,
                "every_row_once": True, "clients_disjoint": True}

    outer = splits(list(range(12)), freeze.audit.OUTER_SEED)
    return {"index_basis": "Zero-based desarrollo_etiquetado.csv order; "
                           "unknown study_index uses desarrollo.csv",
            "known_row_ids": [r["loan_id"] for r in known], "outer": outer,
            "inner_sigmoid_by_outer_train": [
                {"outer_fold": f["fold"], **splits(f["train_indices"], freeze.audit.INNER_SEED)}
                for f in outer["folds"]],
            "inner_sigmoid_full_train": splits(list(range(12)), freeze.audit.INNER_SEED),
            "unknown_study_validation": [{"study_index": 12, "loan_id": "U", "client_id": "C0",
                                          "outer_fold": 0}],
            "capacity_design": "Future fold-specific queue",
            "fallback_policy": "Fixed seeds"}, known, study


def test_saved_partitions_validation_without_cv():
    plan, known, study = saved_plan_template()
    with freeze.audit.no_models_or_generation():
        result = freeze.validate_saved_folds(plan, known, study)
    assert result["validated_partitions"] == 15
    assert result["unknown_assignments"] == 1 and result["known_coverage"] == 12


@pytest.mark.parametrize("mutation", [
    lambda p: p["unknown_study_validation"][0].update(outer_fold=1),
    lambda p: p["unknown_study_validation"].clear(),
    lambda p: p["known_row_ids"].reverse(),
    lambda p: p["outer"]["folds"][0]["train_indices"].append(0),
    lambda p: p["outer"]["folds"][0]["validation_indices"].pop(),
    lambda p: p["inner_sigmoid_by_outer_train"][0]["folds"][0].update(train_clients=["bad"]),
    lambda p: p["inner_sigmoid_full_train"]["folds"][0].update(train_class_counts={"0": 8}),
    lambda p: p.update(unexpected_schema_key=True),
])
def test_saved_fold_tampering_fails(mutation):
    plan, known, study = saved_plan_template()
    mutation(plan)
    with pytest.raises(AssertionError):
        freeze.validate_saved_folds(plan, known, study)


def test_existing_output_fails_before_source_read(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(AssertionError, match="new directory"):
        freeze.freeze(source, source, source, tmp_path)


@pytest.mark.parametrize("shape", ["missing_feature", "extra_feature", "short_row", "extra_cell"])
def test_csv_contract_shape_rejected(tmp_path, shape):
    names = sorted(freeze.audit.ROW_KEYS)
    if shape == "missing_feature":
        names.remove("paid_late")
    if shape == "extra_feature":
        names.append("future_payments")
    cells = ["0"] * len(names)
    if shape == "short_row":
        cells.pop()
    if shape == "extra_cell":
        cells.append("leak")
    path = tmp_path / "rows.csv"
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(names)
        writer.writerow(cells)
    with pytest.raises(AssertionError):
        freeze.read_rows(path)


@pytest.mark.parametrize("method", ["fit", "predict", "predict_proba", "fit_transform",
                                   "generate_owner_pending_dataset"])
def test_guard_blocks_even_indirect_calls(method):
    namespace = {}
    exec(f"def {method}():\n    raise AssertionError('must not reach body')", namespace)
    with pytest.raises(RuntimeError, match="Forbidden"), freeze.audit.no_models_or_generation():
        namespace[method]()
