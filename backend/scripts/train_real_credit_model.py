"""Train only from observed credit outcomes exported from production.

The input CSV must contain the 11 feature columns in ``FEATURE_NAMES`` plus
``defaulted`` (0: paid on time; 1: overdue/default). Synthetic rows are never
accepted by this command.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_NAMES
from app.ml.training import load_real_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path, help="CSV exportado de desenlaces reales")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    x, y = load_real_dataset(args.dataset)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, stratify=y, random_state=42
    )
    pipeline = Pipeline(
        [("scaler", StandardScaler()), ("classifier", LogisticRegression(max_iter=1_000))]
    )
    pipeline.fit(x_train, y_train)
    probability = pipeline.predict_proba(x_test)[:, 1]
    prediction = pipeline.predict(x_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, prediction)),
        "roc_auc": float(roc_auc_score(y_test, probability)),
        "n_rows": int(len(y)),
        "default_rate": float(np.mean(y)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, args.output, compress=3)
    args.output.with_suffix(".json").write_text(
        json.dumps({"feature_names": FEATURE_NAMES, "metrics": metrics}, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
