import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from app.ml.features import FEATURE_NAMES, CreditFeatures

MODEL_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_FILE = MODEL_DIR / "credit_ensemble_v1.joblib"
META_FILE = MODEL_DIR / "credit_ensemble_v1_meta.json"

RULES_VERSION = "rules-v1"
ML_VERSION = "ml-ensemble-v1"


@dataclass(frozen=True)
class ModelResult:
    default_probability: float
    model_score: int
    model_version: str
    ml: bool


_model_cache: tuple[object, list[str], str] | None = None
_model_loaded = False


def _load() -> tuple[object, list[str], str] | None:
    """Carga el pipeline; ante fallo permite reintentar (no cachea errores)."""
    global _model_cache, _model_loaded
    if _model_loaded:
        return _model_cache
    if not MODEL_FILE.exists() or not META_FILE.exists():
        return None
    try:
        meta = json.loads(META_FILE.read_text())
        pipeline = joblib.load(MODEL_FILE)
        feature_names = list(meta["feature_names"])
        if feature_names != FEATURE_NAMES:
            return None
        _model_cache = (pipeline, feature_names, str(meta["version"]))
        _model_loaded = True
    except Exception:
        return None
    return _model_cache


def is_ml_available() -> bool:
    return _load() is not None


def predict_default_probability(features: CreditFeatures) -> ModelResult:
    loaded = _load()
    if loaded is None:
        return ModelResult(
            default_probability=0.0,
            model_score=0,
            model_version=RULES_VERSION,
            ml=False,
        )
    pipeline, _feature_names, version = loaded
    try:
        vector = np.asarray([features.vector()], dtype=float)
        probability = float(pipeline.predict_proba(vector)[0][1])
        default_probability = max(1.0, min(99.0, probability * 100.0))
        model_score = max(0, min(100, round(100.0 * (1.0 - probability))))
        return ModelResult(
            default_probability=default_probability,
            model_score=model_score,
            model_version=version,
            ml=True,
        )
    except Exception:
        return ModelResult(
            default_probability=0.0,
            model_score=0,
            model_version=RULES_VERSION,
            ml=False,
        )