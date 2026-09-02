from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import Credit, CreditStatus, RiskLevel, Sale
from app.models.settings import SETTINGS_ID, BusinessSettings

DEFAULT_MAX_CREDIT_AMOUNT = Decimal("200")


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


async def evaluate_credit(
    db: AsyncSession, client_id: UUID, amount: Decimal
) -> tuple[int, RiskLevel, Decimal, bool]:
    outstanding = await db.scalar(
        select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
            Credit.client_id == client_id,
            Credit.status != CreditStatus.PAID,
        )
    )
    completed_sales = await db.scalar(
        select(func.count(Sale.id)).where(Sale.client_id == client_id)
    )
    debt = Decimal(outstanding or 0)
    loyalty_bonus = min(int(completed_sales or 0), 7)
    debt_penalty = min(float(debt / Decimal("250")), 22)
    amount_penalty = min(float(amount / Decimal("300")), 18)
    score = round(max(30, min(98, 86 - debt_penalty - amount_penalty + loyalty_bonus)))
    risk = risk_from_score(score)
    raw_limit = int(completed_sales or 0) * 100 + score * 12 - float(debt) * 0.2
    recommended_limit = Decimal(max(50, round(raw_limit / 50) * 50))
    recommended_limit = min(recommended_limit, await _max_credit_amount(db))
    approved = amount <= recommended_limit and risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    return score, risk, recommended_limit, approved
