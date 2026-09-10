"""Entrena el modelo de scoring crediticio y guarda el artefacto.

El dataset es sintetico y se genera a partir de las reglas de negocio del
sistema (puntualidad, endeudamiento, volumen, antiguedad y monto solicitado),
de modo que el modelo capture una relacion consistente con el dominio sin
depender de datos historicos reales (la plataforma lleva poco tiempo en uso).

Uso:
    python -m scripts.train_credit_model

Genera:
    backend/app/ml/artifacts/credit_ensemble_v1.joblib
    backend/app/ml/artifacts/credit_ensemble_v1_meta.json
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_NAMES, CreditFeatures

SEED = 42
N_SAMPLES = 4_000
MAX_CREDIT = 200.0
VERSION = "ml-ensemble-v1"
OUT_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"


def _risk_samples(rng: np.random.Generator) -> tuple[list[list[float]], np.ndarray]:
    rows: list[list[float]] = []
    logits: list[float] = []
    for _ in range(N_SAMPLES):
        tenure_days = float(rng.integers(0, 731))
        volume = float(rng.integers(0, 26))
        paid_credits = float(rng.integers(0, 9))
        paid_late = float(rng.integers(0, int(paid_credits) + 1))
        pending_current = float(rng.integers(0, 4))
        pending_overdue = float(rng.integers(0, 4))
        outstanding = float(rng.uniform(0, 501))
        requested_amount = float(rng.uniform(10, 400))

        punctuality_rate = (
            (paid_credits - paid_late) / paid_credits if paid_credits else 0.0
        )
        z = -0.9 * min(1.0, volume / 20.0)
        z -= 1.0 * min(1.0, tenure_days / 365.0)
        if paid_credits:
            z -= 1.1 * punctuality_rate
            if paid_late == paid_credits:
                z += 1.0
        z += 0.7 * min(1.0, pending_overdue)
        z += 0.8 * (outstanding / MAX_CREDIT)
        z += 0.5 * (requested_amount / MAX_CREDIT)
        z += 0.9 * float(rng.normal())

        features = CreditFeatures(
            completed_sales=int(volume),
            paid_credits=int(paid_credits),
            paid_late=int(paid_late),
            pending_overdue=int(pending_overdue),
            pending_current=int(pending_current),
            outstanding=Decimal(str(round(outstanding, 2))),
            requested_amount=Decimal(str(round(requested_amount, 2))),
            max_credit_amount=Decimal(str(MAX_CREDIT)),
            tenure_days=int(tenure_days),
        )
        rows.append(features.vector())
        logits.append(z)
    return rows, np.asarray(logits, dtype=float)


def _balance_shift(logits: np.ndarray) -> float:
    def mean_default(shift: float) -> float:
        return float((1.0 / (1.0 + np.exp(-(logits + shift)))).mean())

    low, high = -5.0, 5.0
    width = high - low
    while width > 1e-6:
        mid = (low + high) / 2.0
        if mean_default(mid) < 0.5:
            low = mid
        else:
            high = mid
        width = high - low
    return (low + high) / 2.0


def generate_dataset(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows, logits = _risk_samples(rng)
    shift = _balance_shift(logits)
    probabilities = 1.0 / (1.0 + np.exp(-(logits + shift)))
    labels = (rng.random(n) < probabilities).astype(int)
    return np.asarray(rows, dtype=float), labels


def build_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                VotingClassifier(
                    estimators=[
                        (
                            "logreg",
                            LogisticRegression(max_iter=1_000, C=1.0, random_state=seed),
                        ),
                        (
                            "random_forest",
                            RandomForestClassifier(
                                n_estimators=250,
                                max_depth=9,
                                min_samples_leaf=4,
                                random_state=seed,
                            ),
                        ),
                    ],
                    voting="soft",
                    weights=[0.45, 0.55],
                ),
            ),
        ]
    )


def _direction_score(probs: list[float]) -> float:
    ranked = np.argsort(np.argsort(probs))
    expected = np.arange(len(probs), dtype=float)
    return float(np.corrcoef(ranked, expected)[0, 1])


def check_monotonic_direction(pipeline: Pipeline) -> dict[str, float]:
    base_features = CreditFeatures(
        completed_sales=3,
        paid_credits=4,
        paid_late=0,
        pending_overdue=0,
        pending_current=1,
        outstanding=Decimal("100"),
        requested_amount=Decimal("150"),
        max_credit_amount=Decimal(str(MAX_CREDIT)),
        tenure_days=360,
    )
    base = base_features.vector()

    def probe(column: int, values: list[float], expect_increasing: bool) -> float:
        probs = []
        for value in values:
            row = list(base)
            row[column] = value
            probs.append(float(pipeline.predict_proba(np.asarray([row], dtype=float))[0][1]))
        correlation = _direction_score(probs)
        return correlation if expect_increasing else -correlation

    directions = {
        "lateness_score_direction": probe(2, [0.0, 1.0, 2.0, 3.0, 4.0], True),
        "pending_overdue_direction": probe(3, [0.0, 1.0, 2.0, 3.0], True),
        "utilization_direction": probe(6, [0.0, 0.5, 1.0, 1.5], True),
        "requested_ratio_direction": probe(7, [0.25, 0.5, 0.75, 1.5], True),
        "overdue_rate_direction": probe(10, [0.0, 0.33, 0.66, 1.0], True),
        "volume_direction": probe(0, [2.0, 6.0, 12.0, 20.0], False),
        "tenure_direction": probe(8, [0.0, 120.0, 365.0, 730.0], False),
        "punctuality_rate_direction": probe(9, [0.0, 0.4, 0.7, 1.0], False),
    }
    for key, score in directions.items():
        if score < 0.5:
            raise RuntimeError(
                f"El modelo aprendio direccion contraria para {key} (score={score:.3f})"
            )
    return directions


def main() -> None:
    x, y = generate_dataset(N_SAMPLES, SEED)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, stratify=y, random_state=SEED
    )

    pipeline = build_pipeline(SEED)
    pipeline.fit(x_train, y_train)

    directions = check_monotonic_direction(pipeline)
    for key, score in directions.items():
        if score < 0.2:
            raise RuntimeError(
                f"El modelo aprendio direccion contraria para {key} (score={score:.3f})"
            )

    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = pipeline.predict(x_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions)),
        "recall": float(recall_score(y_test, predictions)),
        "f1": float(f1_score(y_test, predictions)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "default_rate": float(np.mean(y_test)),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, OUT_DIR / "credit_ensemble_v1.joblib", compress=3)
    meta = {
        "version": VERSION,
        "kind": "voting_ensemble",
        "estimators": ["logistic_regression", "random_forest"],
        "weights": [0.45, 0.55],
        "feature_names": FEATURE_NAMES,
        "n_samples_train": int(len(x_train)),
        "n_samples_test": int(len(x_test)),
        "seed": SEED,
        "metrics": metrics,
        "monotonic_directions": directions,
    }
    (OUT_DIR / "credit_ensemble_v1_meta.json").write_text(
        json.dumps(meta, indent=2) + "\n"
    )

    print(f"Version del modelo: {VERSION}")
    model_path = OUT_DIR / "credit_ensemble_v1.joblib"
    meta_path = OUT_DIR / "credit_ensemble_v1_meta.json"
    print(f"Rutas de artefactos:\n  {model_path}\n  {meta_path}")
    print(f"Direcciones de riesgo (debe ser ~1): {json.dumps(directions)}")
    print(f"Metricas (test): {json.dumps(metrics, indent=2)}")


if __name__ == "__main__":
    main()