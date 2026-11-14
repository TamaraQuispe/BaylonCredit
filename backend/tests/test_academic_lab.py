import hashlib
import json
from types import SimpleNamespace

import joblib
import numpy as np
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sklearn.dummy import DummyClassifier

from app.api.dependencies import get_current_user
from app.api.routes import academic_ml
from app.core.config import Settings
from app.main import app
from app.ml.features import FEATURE_NAMES


@pytest.fixture
def lab(tmp_path, monkeypatch):
    artifact = tmp_path / "academic_model_v2.joblib"
    model = DummyClassifier(strategy="prior").fit(np.zeros((4, 11)), [0, 0, 1, 1])
    joblib.dump(model, artifact)
    report = {
        "data_source": "synthetic",
        "feature_names": FEATURE_NAMES,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "version": "fixture",
        "chosen": {"model": "fixture", "threshold": 0.4},
        "training_rows": 4,
        "validation_rows": 2,
        "final_labeled_rows": 2,
        "fresh_final_checks": {"clients": 1},
        "comparison_on_same_fresh_cohort": {},
    }
    (tmp_path / "experiment_v2_report.json").write_text(json.dumps(report))
    (tmp_path / "academic_lab_cases.json").write_text(
        json.dumps(
            {
                "data_source": "synthetic",
                "cases": [
                    {
                        "id": "FINAL-L1",
                        "scenario": "puntual",
                        "requested_amount": "50",
                        "due_date": "2026-10-01",
                        "actual_late_payment": 0,
                        "features": dict.fromkeys(FEATURE_NAMES, 0),
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(
        academic_ml,
        "get_settings",
        lambda: SimpleNamespace(
            academic_ml_lab_enabled=True,
            environment="staging",
            academic_ml_lab_dir=str(tmp_path),
        ),
    )
    academic_ml.load_lab.cache_clear()
    yield tmp_path
    academic_ml.load_lab.cache_clear()


def test_lab_inference_only_and_case_lookup(lab):
    loaded = academic_ml.laboratory()
    summary = academic_ml.summary(lab=loaded)
    assert summary["data_source"] == "synthetic"
    assert academic_ml.list_cases(lab=loaded)[0]["id"] == "FINAL-L1"
    result = academic_ml.evaluate("FINAL-L1", lab=loaded)
    assert result["estimated_late_probability"] == 0.5
    assert result["predicted_late_payment"] == 1
    assert result["actual_late_payment"] == 0
    with pytest.raises(HTTPException) as error:
        academic_ml.evaluate("../../secret", lab=loaded)
    assert error.value.status_code == 404


def test_production_cannot_enable_academic_lab():
    with pytest.raises(ValueError, match="restricted to staging"):
        Settings(environment="production", academic_ml_lab_enabled=True)


def test_lab_disabled_before_artifact_access(monkeypatch):
    monkeypatch.setattr(
        academic_ml,
        "get_settings",
        lambda: SimpleNamespace(
            academic_ml_lab_enabled=False,
            environment="production",
        ),
    )
    with pytest.raises(HTTPException) as error:
        academic_ml.laboratory()
    assert error.value.status_code == 404


def test_lab_reports_corrupted_artifact_as_unavailable(lab):
    (lab / "academic_model_v2.joblib").write_bytes(b"corrupted")
    with pytest.raises(HTTPException) as error:
        academic_ml.laboratory()
    assert error.value.status_code == 503


async def test_lab_http_requires_login(lab):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/academic-ml/summary")
        assert response.status_code == 401


async def test_lab_authenticated_routes_do_not_call_credit_evaluation(lab, monkeypatch):
    from app.services import credit_scoring

    def unexpected_credit_write(*args, **kwargs):
        raise AssertionError("Academic consultation must not create credit evaluations")

    monkeypatch.setattr(credit_scoring, "evaluate_and_record", unexpected_credit_write)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="operator")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/v1/academic-ml/summary")).json()[
                "data_source"
            ] == "synthetic"
            response = await client.post("/api/v1/academic-ml/evaluate/FINAL-L1")
            assert response.status_code == 200
            assert response.json()["predicted_late_payment"] == 1
            assert (await client.post("/api/v1/academic-ml/evaluate/unknown")).status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
