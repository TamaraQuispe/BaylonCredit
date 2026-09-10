import joblib
import numpy as np

from app.ml.features import FEATURE_NAMES, CreditFeatures
from app.ml.model import META_FILE, MODEL_FILE, _load, predict_default_probability


def _features(good: bool) -> CreditFeatures:
    if good:
        return CreditFeatures(
            completed_sales=18,
            paid_credits=6,
            paid_late=0,
            pending_overdue=0,
            pending_current=1,
            outstanding=30,
            requested_amount=60,
            max_credit_amount=200,
            tenure_days=540,
        )
    return CreditFeatures(
        completed_sales=1,
        paid_credits=1,
        paid_late=1,
        pending_overdue=3,
        pending_current=1,
        outstanding=420,
        requested_amount=380,
        max_credit_amount=200,
        tenure_days=10,
    )


def test_artifact_and_metadata_are_present() -> None:
    assert MODEL_FILE.exists()
    assert META_FILE.exists()
    meta = _load()
    assert meta is not None
    _pipeline, feature_names, version = meta
    assert version.startswith("ml-")
    assert feature_names == FEATURE_NAMES


def test_loaded_pipeline_is_an_ensemble_of_logreg_and_random_forest() -> None:
    pipeline = joblib.load(MODEL_FILE)
    classifier = pipeline.named_steps["classifier"]
    estimator_names = [name for name, _est in classifier.estimators]
    assert "logreg" in estimator_names
    assert "random_forest" in estimator_names
    assert classifier.voting == "soft"


def test_riskier_client_has_higher_default_probability() -> None:
    good = predict_default_probability(_features(good=True))
    bad = predict_default_probability(_features(good=False))
    assert good.ml and bad.ml
    assert bad.default_probability > good.default_probability
    assert bad.model_score < good.model_score


def test_feature_vector_has_expected_length_and_bounds() -> None:
    vector = np.asarray(_features(good=True).vector(), dtype=float)
    assert vector.shape == (len(FEATURE_NAMES),)
    assert 0.0 <= vector[6]  # utilization
    assert 0.0 <= vector[7]  # requested_ratio
    assert vector[9] == 1.0  # puntualidad perfecta
    assert vector[10] == 0.0  # sin créditos vencidos