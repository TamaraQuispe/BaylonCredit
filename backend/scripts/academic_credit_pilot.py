"""Generate and train a standalone SYNTHETIC academic pilot; no DB/network access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
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
from app.ml.outcomes import TARGET_DEFINITION, TARGET_NAME
from app.ml.synthetic import generate_academic_dataset, validate_academic_dataset


def evaluate(model, x, y) -> dict:
    probability, prediction = model.predict_proba(x)[:, 1], model.predict(x)
    return {
        "accuracy": float(accuracy_score(y, prediction)),
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probability)),
        "brier_score": float(brier_score_loss(y, probability)),
        "confusion_matrix_labels_0_1": confusion_matrix(y, prediction, labels=[0, 1]).tolist(),
    }


def run(output: Path, clients: int, seed: int) -> dict:
    if output.resolve().is_relative_to(Path(__file__).resolve().parents[1] / "app"):
        raise ValueError("Academic output cannot be written inside the production app")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Use a new empty output directory to preserve previous evidence")
    dataset = generate_academic_dataset(clients, seed)
    checks = validate_academic_dataset(dataset)
    ledger = output / "synthetic_transactions.json"
    ledger.write_text(json.dumps(dataset, indent=2) + "\n")
    csv_path = output / "synthetic_credit_dataset.csv"
    rows = dataset["rows"]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    partitions = {
        name: [row for row in rows if row["split"] == name and row[TARGET_NAME] is not None]
        for name in ("train", "validation", "test")
    }
    matrices = {}
    for name, records in partitions.items():
        x = np.asarray([[row[feature] for feature in FEATURE_NAMES] for row in records])
        y = np.asarray([row[TARGET_NAME] for row in records], dtype=int)
        if set(y) != {0, 1}:
            raise ValueError(f"Both labels are required in {name}; use more clients")
        matrices[name] = x, y
    x_train, y_train = matrices["train"]
    candidates = {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=120,
            max_depth=5,
            min_samples_leaf=12,
            class_weight="balanced",
            random_state=seed,
            n_jobs=1,
        ),
    }
    validation = {}
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        validation[name] = evaluate(model, *matrices["validation"])
    selected = max(candidates, key=lambda name: validation[name]["f1"])
    model = candidates[selected]
    baseline = DummyClassifier(strategy="prior").fit(x_train, y_train)
    metrics = evaluate(model, *matrices["test"])
    predictions = model.predict(matrices["test"][0])
    probabilities = model.predict_proba(matrices["test"][0])[:, 1]
    with (output / "synthetic_test_predictions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "data_source",
                "client_id",
                "loan_id",
                TARGET_NAME,
                "predicted_late_payment",
                "estimated_probability",
            ]
        )
        for row, prediction, probability in zip(
            partitions["test"], predictions, probabilities, strict=True
        ):
            writer.writerow(
                [
                    "synthetic",
                    row["client_id"],
                    row["loan_id"],
                    row[TARGET_NAME],
                    int(prediction),
                    float(probability),
                ]
            )
    joblib.dump(model, output / "academic_synthetic_late_payment.joblib")
    report = {
        "version": "academic-synthetic-late-v1",
        "data_source": "synthetic",
        "generated_utc": datetime.now(UTC).isoformat(),
        "seed": seed,
        "teacher_permission": "Reported by the user; no independent teacher message attached",
        "scope": (
            "Academic experiment only. No production changes, real personal data, "
            "or business-performance validation."
        ),
        "simulated_period": {
            "start": min(row["evaluated_at"] for row in rows),
            "observation_cutoff": dataset["observed_on"],
        },
        "target": TARGET_NAME,
        "target_definition": TARGET_DEFINITION,
        "features": FEATURE_NAMES,
        "excluded_from_features": [
            "profile",
            "scenario",
            "pending_at_cutoff",
            "late_payment",
            "client_id",
            "loan_id",
            "split",
        ],
        "split": (
            "60/20/20 by fictional client; assigned before simulation, "
            "no client crosses partitions"
        ),
        "class_counts": {
            name: {
                str(label): int(sum(row[TARGET_NAME] == label for row in records))
                for label in (0, 1)
            }
            for name, records in partitions.items()
        },
        "clients_per_split": {
            name: len({c["client_id"] for c in dataset["clients"] if c["split"] == name})
            for name in partitions
        },
        "consistency": checks,
        "validation_metrics": validation,
        "selection": "Highest validation F1, no selection or tuning on test",
        "selected_model": selected,
        "threshold": 0.5,
        "held_out_synthetic_test_metrics": metrics,
        "baseline_synthetic_test_metrics": evaluate(baseline, *matrices["test"]),
        "sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [csv_path, ledger]
        },
        "limitations": [
            "Simulation assumptions, not estimated business distributions",
            "No guarantee of real-world performance or calibrated probabilities",
            "Synthetic granted credits are observations, not automatic approval recommendations",
            "The 5% loss-to-sales estimate is not used as the lateness/target distribution",
            "Unresolved cases excluded, IDs and future outcomes not used as predictors",
        ],
    }
    (output / "academic_synthetic_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "README.md").write_text(
        "# Piloto académico con datos SINTÉTICOS\n\n"
        "No son operaciones reales de Cervecería Baylón. No cargar en producción "
        "ni usar para afirmar reducción de pérdidas.\n\n"
        f"Semilla: {seed}. Clientes ficticios: {clients}. Fiados: {checks['loans']}. "
        f"Modelo seleccionado con validación: {selected}.\n\n"
        "Se simulan eventos de compra, fiado a un día y pagos. "
        "Snapshots recomputados antes del crédito; etiquetas derivadas de pagos "
        "y vencimiento, no copiadas del score. "
        "Hay pago temprano, puntual, abonos puntuales/tardíos, atraso corto/largo, "
        "impago observado, abono incompleto y casos sin desenlace.\n\n"
        "Cada cliente pertenece a una sola partición 60/20/20. "
        "Entrenamiento y escalado solo en train, selección por F1 en validation, "
        "evaluación final en test. "
        "Ninguna métrica demuestra precisión con clientes reales. "
        "Dataset, ledger, predicciones, reporte y artefacto tienen nombres "
        "académicos/sintéticos separados del loader productivo.\n"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--clients", type=int, default=180)
    parser.add_argument("--seed", type=int, default=20261028)
    args = parser.parse_args()
    result = run(args.output_dir, args.clients, args.seed)
    print(
        json.dumps(
            {
                "synthetic": True,
                "consistency": result["consistency"],
                "selected_model": result["selected_model"],
                "synthetic_test_metrics": result["held_out_synthetic_test_metrics"],
            },
            indent=2,
        )
    )
