from dataclasses import asdict, dataclass
from decimal import Decimal
from time import perf_counter
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import collect_credit_features
from app.ml.model import RULES_VERSION, predict_default_probability
from app.models.client import Client
from app.models.commerce import (
    CreditEvaluation,
    RiskLevel,
)
from app.models.settings import SETTINGS_ID, BusinessSettings

DEFAULT_MAX_CREDIT_AMOUNT = Decimal("200")
CreditEvaluationSource = Literal["manual", "direct_credit", "credit_sale"]

MAX_SCORE = 100
INITIAL_CREDIT_SCORE = 50
ML_MODEL_WEIGHT = 0.7
RULE_MODEL_WEIGHT = 0.3


@dataclass(frozen=True)
class ScoreFactor:
    key: str
    label: str
    weight: int
    contribution: int
    description: str


@dataclass(frozen=True)
class EvaluationResult:
    score: int
    risk: RiskLevel
    recommended_limit: Decimal
    approved: bool
    factors: list[ScoreFactor]
    default_probability: int
    confidence: int
    model_version: str


def risk_from_score(score: int) -> RiskLevel:
    if score >= 88:
        return RiskLevel.VERY_LOW
    if score >= 76:
        return RiskLevel.LOW
    if score >= 61:
        return RiskLevel.MEDIUM
    if score >= 46:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def _volume_contribution(completed_sales: int) -> int:
    return min(completed_sales * 5, 25)


def _punctuality_contribution(paid_on_time: int, overdue: int) -> int:
    base = min(paid_on_time * 8, 20)
    if overdue:
        base = max(0, base - 12)
    return base


def _debt_contribution(debt: Decimal) -> int:
    return max(0, 30 - int(debt / Decimal("10")))


def _amount_contribution(amount: Decimal, max_credit_amount: Decimal) -> int:
    ratio = float(amount / max_credit_amount) if max_credit_amount else 1.0
    return max(0, 15 - int(ratio * 15))


def _tenure_contribution(tenure_days: int) -> int:
    return min(tenure_days // 36, 10)


async def _max_credit_amount(db: AsyncSession) -> Decimal:
    settings = await db.get(BusinessSettings, SETTINGS_ID)
    return settings.max_credit_amount if settings else DEFAULT_MAX_CREDIT_AMOUNT


async def evaluate_credit(
    db: AsyncSession, client_id: UUID, amount: Decimal
) -> EvaluationResult:
    client = await db.get(Client, client_id)
    max_credit_amount = await _max_credit_amount(db)
    features = await collect_credit_features(db, client, amount, max_credit_amount)

    debt = features.outstanding
    volume = _volume_contribution(features.completed_sales)
    paid_on_time = features.paid_credits - features.paid_late
    punctuality = _punctuality_contribution(
        paid_on_time, features.pending_overdue + features.paid_late
    )
    debt_factor = _debt_contribution(debt)
    amount_factor = _amount_contribution(amount, max_credit_amount)
    tenure = _tenure_contribution(features.tenure_days)

    rules_score = INITIAL_CREDIT_SCORE + sum(
        [volume, punctuality, debt_factor, amount_factor, tenure]
    )
    rules_score = max(0, min(rules_score, MAX_SCORE))

    model = predict_default_probability(features)
    if model.ml:
        default_probability = int(round(model.default_probability))
        confidence = max(0, min(100, round(50 + abs(model.default_probability - 50))))
        model_version = model.model_version
        cold_start = (
            features.completed_sales == 0
            and features.paid_credits == 0
            and features.pending_current == 0
            and features.pending_overdue == 0
            and features.tenure_days == 0
        )
        if cold_start:
            score = rules_score
            default_probability = max(2, 100 - score)
            confidence = min(100, 40 + score // 5)
        else:
            score = round(
                ML_MODEL_WEIGHT * model.model_score + RULE_MODEL_WEIGHT * rules_score
            )
            score = max(0, min(score, MAX_SCORE))
    else:
        score = rules_score
        default_probability = max(2, 100 - score)
        confidence = min(100, 50 + (score * 40) // 500)
        model_version = RULES_VERSION

    risk = risk_from_score(score)
    raw_limit = int(features.completed_sales) * 80 + score * 10 - float(debt) * 0.2
    recommended_limit = Decimal(max(50, round(raw_limit / 50) * 50))
    recommended_limit = min(recommended_limit, max_credit_amount)
    approved = (
        amount <= recommended_limit and risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    )

    factors = [
        ScoreFactor(
            key="volume",
            label="Historial de ventas",
            weight=25,
            contribution=volume,
            description=f"{features.completed_sales} compras registradas.",
        ),
        ScoreFactor(
            key="punctuality",
            label="Puntualidad de pagos",
            weight=20,
            contribution=punctuality,
            description=(
                f"{paid_on_time} pagados puntualmente, {features.paid_late} pagados "
                f"con atraso, {features.pending_overdue} pendientes vencidos."
            ),
        ),
        ScoreFactor(
            key="debt",
            label="Nivel de endeudamiento",
            weight=30,
            contribution=debt_factor,
            description=f"Deuda pendiente de {debt}.",
        ),
        ScoreFactor(
            key="amount",
            label="Monto solicitado",
            weight=15,
            contribution=amount_factor,
            description=(
                f"Solicita {amount} de un tope de {max_credit_amount}."
            ),
        ),
        ScoreFactor(
            key="tenure",
            label="Antigüedad del cliente",
            weight=10,
            contribution=tenure,
            description="Cliente reciente con historial limitado.",
        ),
    ]

    return EvaluationResult(
        score=score,
        risk=risk,
        recommended_limit=recommended_limit,
        approved=approved,
        factors=factors,
        default_probability=default_probability,
        confidence=confidence,
        model_version=model_version,
    )


async def evaluate_and_record(
    db: AsyncSession,
    client_id: UUID,
    amount: Decimal,
    created_by_id: UUID | None,
    source: CreditEvaluationSource,
) -> CreditEvaluation:
    started_at = perf_counter()
    result = await evaluate_credit(db, client_id, amount)
    recommendation = (
        f"Credit approved up to S/ {result.recommended_limit}."
        if result.approved
        else f"Amount exceeds the recommended limit of S/ {result.recommended_limit}."
    )
    evaluation = CreditEvaluation(
        client_id=client_id,
        created_by_id=created_by_id,
        requested_amount=amount,
        score=result.score,
        risk=result.risk,
        default_probability=result.default_probability,
        recommended_limit=result.recommended_limit,
        approved=result.approved,
        recommendation=recommendation,
        confidence=result.confidence,
        factors=[asdict(factor) for factor in result.factors],
        model_version=result.model_version,
        source=source,
        response_time_ms=round((perf_counter() - started_at) * 1000),
    )
    db.add(evaluation)
    return evaluation