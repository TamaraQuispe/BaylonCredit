import json
import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import BackgroundTasks
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.commerce import CreditEvaluation

logger = logging.getLogger(__name__)
PROMPT_VERSION = "credit-explanation-v1"


class AiCreditAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation: str = Field(min_length=20, max_length=1200)
    risk_factors: list[str] = Field(max_length=5)
    recommendations: list[str] = Field(max_length=5)


class AiCreditError(RuntimeError):
    pass


def _request_payload(evaluation: CreditEvaluation) -> dict:
    factors = [
        {
            "key": factor.get("key"),
            "label": factor.get("label"),
            "contribution": factor.get("contribution"),
            "weight": factor.get("weight"),
            "category": factor.get("category"),
        }
        for factor in evaluation.factors
    ]
    data = {
        "requested_amount_pen": str(evaluation.requested_amount),
        "score": evaluation.score,
        "risk": evaluation.risk.value,
        "default_probability_percent": evaluation.default_probability,
        "recommended_limit_pen": str(evaluation.recommended_limit),
        "approved": evaluation.approved,
        "confidence_percent": evaluation.confidence,
        "deterministic_recommendation": evaluation.recommendation,
        "factors": factors,
    }
    return {
        "model": get_settings().openrouter_model,
        "temperature": 0.2,
        "max_tokens": 1600,
        "reasoning": {"effort": "low", "exclude": True},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres una capa explicativa de riesgo crediticio para Credifycredit. "
                    "Explica en español simple el resultado ya calculado. No cambies la "
                    "decisión, score, riesgo ni límite; no inventes datos, atributos personales "
                    "ni causas discriminatorias. Devuelve únicamente el JSON solicitado."
                ),
            },
            {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "credit_analysis",
                "strict": True,
                "schema": AiCreditAnalysis.model_json_schema(),
            },
        },
    }


async def generate_credit_analysis(
    evaluation: CreditEvaluation,
) -> tuple[AiCreditAnalysis, str]:
    settings = get_settings()
    if not settings.openrouter_enabled or not settings.openrouter_api_key:
        raise AiCreditError("OpenRouter is disabled")
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
    }
    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=settings.openrouter_timeout_seconds) as client:
            response = await client.post(url, json=_request_payload(evaluation), headers=headers)
    except httpx.HTTPError as exc:
        raise AiCreditError("OpenRouter request failed") from exc
    if response.status_code != 200:
        raise AiCreditError(f"OpenRouter responded {response.status_code}")
    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        analysis = AiCreditAnalysis.model_validate_json(content)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AiCreditError("OpenRouter returned an invalid structured response") from exc
    return analysis, str(body.get("model") or settings.openrouter_model)


async def dispatch_ai_explanation(evaluation_id: UUID) -> None:
    settings = get_settings()
    if not (settings.openrouter_enabled and settings.openrouter_api_key):
        return
    async with SessionFactory() as db:
        evaluation = await db.get(CreditEvaluation, evaluation_id)
        if evaluation is None:
            return
        try:
            analysis, model = await generate_credit_analysis(evaluation)
        except Exception:
            logger.exception("Failed to generate AI explanation for evaluation %s", evaluation_id)
            evaluation.ai_status = "failed"
        else:
            evaluation.ai_explanation = analysis.explanation
            evaluation.ai_risk_factors = analysis.risk_factors
            evaluation.ai_recommendations = analysis.recommendations
            evaluation.ai_status = "completed"
            evaluation.ai_model = model
            evaluation.ai_prompt_version = PROMPT_VERSION
            evaluation.ai_generated_at = datetime.now(UTC)
        await db.commit()


def enqueue_ai_explanation(background_tasks: BackgroundTasks, evaluation_id: UUID) -> None:
    settings = get_settings()
    if settings.openrouter_enabled and settings.openrouter_api_key:
        background_tasks.add_task(dispatch_ai_explanation, evaluation_id)
