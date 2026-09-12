import json
from decimal import Decimal
from uuid import uuid4

import pytest

import app.services.ai_credit as ai_credit
from app.core.config import Settings
from app.models.commerce import CreditEvaluation, RiskLevel


def _settings(**overrides) -> Settings:
    base = {
        "openrouter_enabled": True,
        "openrouter_api_key": "test-openrouter-key",
        "openrouter_model": "openai/gpt-4o-mini",
        "openrouter_timeout_seconds": 3,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def _evaluation() -> CreditEvaluation:
    return CreditEvaluation(
        client_id=uuid4(),
        created_by_id=None,
        requested_amount=Decimal("500.00"),
        score=78,
        risk=RiskLevel.MEDIUM,
        default_probability=22,
        recommended_limit=Decimal("600.00"),
        approved=True,
        recommendation="Crédito aprobado por el motor determinístico.",
        confidence=82,
        factors=[
            {
                "key": "punctuality",
                "label": "Puntualidad de pagos",
                "weight": 20,
                "contribution": 16,
                "description": "Dato agregado.",
                "category": "positivo",
            }
        ],
        model_version="ml-ensemble-v1",
        source="manual",
        response_time_ms=20,
        ai_status="pending",
    )


class _FakeResponse:
    def __init__(self, status_code: int = 200, content: str | None = None) -> None:
        self.status_code = status_code
        self._content = content or json.dumps(
            {
                "explanation": "El historial agregado respalda la decisión calculada.",
                "risk_factors": ["Riesgo medio según el score"],
                "recommendations": ["Mantener seguimiento de pagos"],
            }
        )

    def json(self) -> dict:
        return {
            "model": "openai/gpt-4o-mini",
            "choices": [{"message": {"content": self._content}}],
        }


class _FakeAsyncClient:
    captured: tuple[str, dict, dict] | None = None
    response = _FakeResponse()

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
        type(self).captured = (url, json, headers)
        return type(self).response


async def test_generate_credit_analysis_uses_structured_anonymous_payload(monkeypatch) -> None:
    monkeypatch.setattr(ai_credit, "get_settings", lambda: _settings())
    monkeypatch.setattr(ai_credit.httpx, "AsyncClient", _FakeAsyncClient)

    analysis, model = await ai_credit.generate_credit_analysis(_evaluation())

    assert model == "openai/gpt-4o-mini"
    assert analysis.risk_factors == ["Riesgo medio según el score"]
    url, payload, headers = _FakeAsyncClient.captured
    assert url.endswith("/chat/completions")
    assert payload["response_format"]["type"] == "json_schema"
    schema = payload["response_format"]["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"explanation", "risk_factors", "recommendations"}
    serialized_prompt = payload["messages"][1]["content"]
    assert "client_id" not in serialized_prompt
    assert "document" not in serialized_prompt
    assert "phone" not in serialized_prompt
    assert headers["Authorization"] == "Bearer test-openrouter-key"


async def test_generate_credit_analysis_rejects_remote_error(monkeypatch) -> None:
    monkeypatch.setattr(ai_credit, "get_settings", lambda: _settings())
    monkeypatch.setattr(ai_credit.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(_FakeAsyncClient, "response", _FakeResponse(status_code=401))

    with pytest.raises(ai_credit.AiCreditError, match="responded 401"):
        await ai_credit.generate_credit_analysis(_evaluation())


async def test_generate_credit_analysis_rejects_invalid_json(monkeypatch) -> None:
    monkeypatch.setattr(ai_credit, "get_settings", lambda: _settings())
    monkeypatch.setattr(ai_credit.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(_FakeAsyncClient, "response", _FakeResponse(content="not-json"))

    with pytest.raises(ai_credit.AiCreditError, match="invalid structured response"):
        await ai_credit.generate_credit_analysis(_evaluation())


async def test_generate_credit_analysis_is_disabled_by_default() -> None:
    with pytest.raises(ai_credit.AiCreditError, match="disabled"):
        await ai_credit.generate_credit_analysis(_evaluation())
