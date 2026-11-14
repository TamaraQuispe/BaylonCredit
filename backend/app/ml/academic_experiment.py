"""Model/threshold selection for the isolated synthetic academic laboratory."""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_NAMES

THRESHOLDS = tuple(round(0.2 + step * 0.05, 2) for step in range(13))
MIN_RECALL = 0.30


def metrics(y, probability, threshold: float) -> dict:
    prediction = np.asarray(probability) >= threshold
    return {
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probability)),
        "brier_score": float(brier_score_loss(y, probability)),
        "confusion_matrix": confusion_matrix(y, prediction, labels=[0, 1]).tolist(),
    }


def select_validation_candidate(candidates: list[dict]) -> dict:
    """Maximize validation accuracy with recall floor; never inspect final-test labels."""
    eligible = [
        candidate for candidate in candidates if candidate["metrics"]["recall"] >= MIN_RECALL
    ]
    if not eligible:
        raise ValueError("No candidate meets the preregistered validation recall floor")
    return max(
        eligible,
        key=lambda candidate: (
            candidate["metrics"]["accuracy"],
            candidate["metrics"]["balanced_accuracy"],
            candidate["metrics"]["f1"],
            -abs(candidate["threshold"] - 0.5),
        ),
    )


def build_candidates(seed: int) -> dict:
    models = {}
    for weight in (None, "balanced"):
        for strength in (0.1, 1.0, 10.0):
            name = f"logistic_C{strength}_{weight or 'unweighted'}"
            models[name] = make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    C=strength, class_weight=weight, max_iter=2000, random_state=seed
                ),
            )
        for depth in (3, 6):
            name = f"forest_depth{depth}_{weight or 'unweighted'}"
            models[name] = RandomForestClassifier(
                n_estimators=150,
                max_depth=depth,
                min_samples_leaf=12,
                class_weight=weight,
                random_state=seed,
                n_jobs=1,
            )
    return models


def matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.asarray([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float),
        np.asarray([row["late_payment"] for row in rows], dtype=int),
    )


def error_analysis(rows: list[dict], probability, threshold: float) -> dict:
    counts: dict[str, dict[str, int]] = {}
    examples: list[dict] = []
    for row, risk in zip(rows, probability, strict=True):
        predicted = int(risk >= threshold)
        actual = int(row["late_payment"])
        kind = "TP" if actual and predicted else "FN" if actual else "FP" if predicted else "TN"
        segment = "sin_pagos_previos" if row["paid_credits"] == 0 else "con_pagos_previos"
        for group in (segment, row["scenario"]):
            counts.setdefault(group, {"TP": 0, "FN": 0, "FP": 0, "TN": 0})[kind] += 1
        if kind in {"FP", "FN"} and sum(item["error"] == kind for item in examples) < 6:
            examples.append(
                {
                    "data_source": "synthetic",
                    "loan_id": row["loan_id"],
                    "scenario": row["scenario"],
                    "error": kind,
                    "estimated_probability": float(risk),
                    "actual": actual,
                    "paid_credits_before": row["paid_credits"],
                    "paid_late_before": row["paid_late"],
                    "outstanding_before": row["outstanding"],
                }
            )
    return {"counts": counts, "examples": examples}
