from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from time import perf_counter
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.commerce import (
    Credit,
    CreditEvaluation,
    Payment,
    PaymentAllocation,
    RiskLevel,
    Sale,
)
from app.models.settings import SETTINGS_ID, BusinessSettings

DEFAULT_MAX_CREDIT_AMOUNT = Decimal("200")
CreditEvaluationSource = Literal["manual", "direct_credit", "credit_sale"]

MAX_SCORE = 100
INITIAL_CREDIT_SCORE = 50


@dataclass(frozen=True)
class ScoreFactor:
    key: str
    label: str
    weight: int
    contribution: int
    description: str


async def _max_credit_amount(db: AsyncSession) -> Decimal:
    settings = await db.get(BusinessSettings, SETTINGS_ID)
    return settings.max_credit_amount if settings else DEFAULT_MAX_CREDIT_AMOUNT


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


def _punctuality_contribution(paid_credits: int, overdue_credits: int) -> int:
    base = min(paid_credits * 8, 20)
    if overdue_credits:
        base = max(0, base - 12)
    return base


def _debt_contribution(debt: Decimal) -> int:
    return max(0, 30 - int(debt / Decimal("10")))


def _amount_contribution(amount: Decimal, max_credit_amount: Decimal) -> int:
    ratio = float(amount / max_credit_amount) if max_credit_amount else 1.0
    return max(0, 15 - int(ratio * 15))


def _tenure_contribution(client_created_at) -> int:
    if client_created_at is None:
        return 0
    days = max(0, (date.today() - client_created_at.date()).days)
    return min(days // 36, 10)


async def evaluate_credit(
    db: AsyncSession, client_id: UUID, amount: Decimal
) -> tuple[int, RiskLevel, Decimal, bool, list[ScoreFactor]]:
    client = await db.get(Client, client_id)
    outstanding = await db.scalar(
        select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
            Credit.client_id == client_id,
            Credit.pending_amount > 0,
        )
    )
    completed_sales = await db.scalar(
        select(func.count(Sale.id)).where(Sale.client_id == client_id)
    )
    paid_credits = int(
        await db.scalar(
            select(func.count(Credit.id)).where(
                Credit.client_id == client_id,
                Credit.pending_amount == 0,
            )
        )
        or 0
    )
    pending_overdue = int(
        await db.scalar(
            select(func.count(Credit.id)).where(
                Credit.client_id == client_id,
                Credit.pending_amount > 0,
                Credit.due_date < date.today(),
            )
        )
        or 0
    )
    paid_late = int(
        await db.scalar(
            select(func.count(func.distinct(Credit.id)))
            .join(PaymentAllocation, PaymentAllocation.credit_id == Credit.id)
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(
                Credit.client_id == client_id,
                Credit.pending_amount == 0,
                Payment.payment_date > Credit.due_date,
            )
        )
        or 0
    )
    max_credit_amount = await _max_credit_amount(db)

    debt = Decimal(outstanding or 0)
    volume = _volume_contribution(int(completed_sales or 0))
    paid_on_time = paid_credits - paid_late
    punctuality = _punctuality_contribution(paid_on_time, pending_overdue + paid_late)
    debt_factor = _debt_contribution(debt)
    amount_factor = _amount_contribution(amount, max_credit_amount)
    tenure = _tenure_contribution(client.created_at if client else None)

    score = INITIAL_CREDIT_SCORE + sum(
        [volume, punctuality, debt_factor, amount_factor, tenure]
    )
    score = max(0, min(score, MAX_SCORE))
    risk = risk_from_score(score)
    raw_limit = int(completed_sales or 0) * 80 + score * 10 - float(debt) * 0.2
    recommended_limit = Decimal(max(50, round(raw_limit / 50) * 50))
    recommended_limit = min(recommended_limit, max_credit_amount)
    approved = amount <= recommended_limit and risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL}

    factors = [
        ScoreFactor(
            key="volume",
            label="Historial de ventas",
            weight=25,
            contribution=volume,
            description=f"{int(completed_sales or 0)} compras registradas.",
        ),
        ScoreFactor(
            key="punctuality",
            label="Puntualidad de pagos",
            weight=20,
            contribution=punctuality,
            description=(
                f"{paid_on_time} pagados puntualmente, {paid_late} pagados con atraso, "
                f"{pending_overdue} pendientes vencidos."
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
            description=f"Solicita {amount} de un tope de {max_credit_amount}.",
        ),
        ScoreFactor(
            key="tenure",
            label="Antigüedad del cliente",
            weight=10,
            contribution=tenure,
            description="Cliente reciente con historial limitado.",
        ),
    ]

    return score, risk, recommended_limit, approved, factors


async def evaluate_and_record(
    db: AsyncSession,
    client_id: UUID,
    amount: Decimal,
    created_by_id: UUID | None,
    source: CreditEvaluationSource,
) -> CreditEvaluation:
    started_at = perf_counter()
    score, risk, recommended_limit, approved, factors = await evaluate_credit(
        db, client_id, amount
    )
    max_weight = sum(factor.weight for factor in factors) or 1
    confidence = min(100, 50 + len(factors) * 10 + (score * 40) // (5 * max_weight))
    recommendation = (
        f"Credit approved up to S/ {recommended_limit}."
        if approved
        else f"Amount exceeds the recommended limit of S/ {recommended_limit}."
    )
    evaluation = CreditEvaluation(
        client_id=client_id,
        created_by_id=created_by_id,
        requested_amount=amount,
        score=score,
        risk=risk,
        default_probability=max(2, 100 - score),
        recommended_limit=recommended_limit,
        approved=approved,
        recommendation=recommendation,
        confidence=confidence,
        factors=[asdict(factor) for factor in factors],
        source=source,
        response_time_ms=round((perf_counter() - started_at) * 1000),
    )
    db.add(evaluation)
    return evaluation
