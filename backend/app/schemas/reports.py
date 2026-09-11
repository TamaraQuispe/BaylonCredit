from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.commerce import RiskLevel


class PortfolioClientReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: UUID
    client_name: str
    business_name: str | None
    total_pending: Decimal
    total_overdue: Decimal
    active_credits: int
    overdue_credits: int
    earliest_due: date | None


class PortfolioSummary(BaseModel):
    total_pending: Decimal
    total_overdue: Decimal
    total_recovered: Decimal
    delinquency_rate: float
    active_credits: int
    overdue_credits: int
    due_soon_credits: int
    paid_credits: int
    generated_at: date


class PortfolioReportRead(BaseModel):
    summary: PortfolioSummary
    clients: list[PortfolioClientReport]


class ClientRiskReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: UUID
    client_name: str
    business_name: str | None
    phone: str | None
    score: int | None
    risk: RiskLevel | None
    last_evaluation_at: datetime | None
    recommendation: str | None
    assigned_line: Decimal
    used: Decimal
    available: Decimal
    utilization_percent: float
    pending_amount: Decimal
    overdue_amount: Decimal
    overdue_credits: int
    max_overdue_days: int
    next_due_date: date | None


class RiskReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: date
    clients: list[ClientRiskReport]