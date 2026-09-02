from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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