from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.commerce import Credit, Payment, PaymentAllocation, Sale

FEATURE_NAMES = [
    "completed_sales",
    "paid_credits",
    "paid_late",
    "pending_overdue",
    "pending_current",
    "outstanding",
    "utilization",
    "requested_ratio",
    "tenure_days",
    "punctuality_rate",
    "overdue_rate",
]


@dataclass(frozen=True)
class CreditFeatures:
    completed_sales: int
    paid_credits: int
    paid_late: int
    pending_overdue: int
    pending_current: int
    outstanding: Decimal
    requested_amount: Decimal
    max_credit_amount: Decimal
    tenure_days: int

    @property
    def utilization(self) -> float:
        return float(self.outstanding / self.max_credit_amount) if self.max_credit_amount else 0.0

    @property
    def requested_ratio(self) -> float:
        if not self.max_credit_amount:
            return 1.0
        return float(self.requested_amount / self.max_credit_amount)

    @property
    def punctuality_rate(self) -> float:
        if not self.paid_credits:
            return 0.0
        return max(0.0, (self.paid_credits - self.paid_late) / self.paid_credits)

    @property
    def overdue_rate(self) -> float:
        active = self.pending_current + self.pending_overdue
        if not active:
            return 0.0
        return self.pending_overdue / active

    def vector(self) -> list[float]:
        return [
            float(self.completed_sales),
            float(self.paid_credits),
            float(self.paid_late),
            float(self.pending_overdue),
            float(self.pending_current),
            float(self.outstanding),
            self.utilization,
            self.requested_ratio,
            float(self.tenure_days),
            self.punctuality_rate,
            self.overdue_rate,
        ]


async def collect_credit_features(
    db: AsyncSession,
    client: Client,
    amount: Decimal,
    max_credit_amount: Decimal,
) -> CreditFeatures:
    outstanding = await db.scalar(
        select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
            Credit.client_id == client.id,
            Credit.pending_amount > 0,
        )
    )
    completed_sales = await db.scalar(
        select(func.count(Sale.id)).where(Sale.client_id == client.id)
    )
    paid_credits = int(
        await db.scalar(
            select(func.count(Credit.id)).where(
                Credit.client_id == client.id,
                Credit.pending_amount == 0,
            )
        )
        or 0
    )
    pending_overdue = int(
        await db.scalar(
            select(func.count(Credit.id)).where(
                Credit.client_id == client.id,
                Credit.pending_amount > 0,
                Credit.due_date < date.today(),
            )
        )
        or 0
    )
    pending_current = int(
        await db.scalar(
            select(func.count(Credit.id)).where(
                Credit.client_id == client.id,
                Credit.pending_amount > 0,
                Credit.due_date >= date.today(),
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
                Credit.client_id == client.id,
                Credit.pending_amount == 0,
                Payment.payment_date > Credit.due_date,
            )
        )
        or 0
    )
    tenure_days = 0
    if client.created_at is not None:
        tenure_days = max(0, (date.today() - client.created_at.date()).days)
    return CreditFeatures(
        completed_sales=int(completed_sales or 0),
        paid_credits=paid_credits,
        paid_late=paid_late,
        pending_overdue=pending_overdue,
        pending_current=pending_current,
        outstanding=Decimal(outstanding or 0),
        requested_amount=amount,
        max_credit_amount=max_credit_amount,
        tenure_days=tenure_days,
    )