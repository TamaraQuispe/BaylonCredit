import numpy as np
import pytest

from app.ml.academic_experiment import (
    MIN_RECALL,
    THRESHOLDS,
    error_analysis,
    matrix,
    metrics,
    select_validation_candidate,
)
from app.ml.features import FEATURE_NAMES


def candidate(accuracy, recall, balanced=0.6):
    return {
        "model": "fixture",
        "threshold": 0.5,
        "metrics": {
            "accuracy": accuracy,
            "recall": recall,
            "balanced_accuracy": balanced,
            "f1": 0.5,
        },
    }


def test_selection_never_rewards_majority_without_recall():
    majority = candidate(0.95, 0)
    useful = candidate(0.7, MIN_RECALL)
    assert select_validation_candidate([majority, useful]) is useful


def test_selection_uses_accuracy_only_within_recall_guardrail():
    first, second = candidate(0.6, 0.9), candidate(0.7, 0.4)
    assert select_validation_candidate([first, second]) is second
    with pytest.raises(ValueError, match="recall"):
        select_validation_candidate([candidate(0.9, 0.1)])


def test_predictors_exclude_future_outcomes_and_metadata():
    row = {name: 0 for name in FEATURE_NAMES}
    row.update(late_payment=1, pending_at_cutoff=999, scenario="future", client_id="ID")
    x, y = matrix([row])
    assert x.shape == (1, 11)
    assert x.sum() == 0
    assert y.tolist() == [1]


def test_threshold_changes_confusion_counts_not_auc():
    y = np.array([0, 0, 1, 1])
    low, high = metrics(y, [0.1, 0.4, 0.45, 0.9], 0.4), metrics(y, [0.1, 0.4, 0.45, 0.9], 0.5)
    assert low["recall"] == 1
    assert high["recall"] == 0.5
    assert low["roc_auc"] == high["roc_auc"] == 1
    assert min(THRESHOLDS) == 0.2 and max(THRESHOLDS) == 0.8


def test_errors_identify_fp_and_fn_not_personal_data():
    rows = [
        dict(
            loan_id="L1",
            scenario="puntual",
            late_payment=0,
            paid_credits=0,
            paid_late=0,
            outstanding=0,
        ),
        dict(
            loan_id="L2",
            scenario="atraso_corto",
            late_payment=1,
            paid_credits=2,
            paid_late=0,
            outstanding=20,
        ),
    ]
    report = error_analysis(rows, [0.9, 0.1], 0.5)
    assert report["counts"]["sin_pagos_previos"]["FP"] == 1
    assert report["counts"]["con_pagos_previos"]["FN"] == 1
    assert {example["error"] for example in report["examples"]} == {"FP", "FN"}
