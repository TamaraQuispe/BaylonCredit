from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.commerce import RiskLevel


class CreditEvaluationRequest(BaseModel):
    client_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class CreditEvaluationRead(BaseModel):
    score: int
    risk: RiskLevel
    default_probability: int
    recommended_limit: Decimal
    approved: bool
    recommendation: str
    calculated_at: datetime
    response_time_ms: int


class DirectCreditCreate(BaseModel):
    client_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    credit_date: date
    due_date: date
    manual_override: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "DirectCreditCreate":
        if self.due_date <= self.credit_date:
            raise ValueError("Due date must be after credit date")
        if self.credit_date > date.today():
            raise ValueError("Credit date cannot be in the future")
        return self


class CreditPaymentEntry(BaseModel):
    id: UUID
    payment_id: UUID
    amount: Decimal
    payment_date: date
    method: str
    reference: str | None
    created_at: datetime


class FinanceCreditRead(BaseModel):
    id: UUID
    code: str
    client_id: UUID
    client_name: str
    client_business: str
    client_phone: str
    original_amount: Decimal
    pending_amount: Decimal
    paid_amount: Decimal
    paid_percent: float
    credit_date: date
    due_date: date
    status: str
    risk: RiskLevel
    score: int
    recommended_limit: Decimal
    created_at: datetime
    payments: list[CreditPaymentEntry]


class PaymentAllocationCreate(BaseModel):
    credit_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PaymentCreate(BaseModel):
    client_id: UUID
    allocations: list[PaymentAllocationCreate] = Field(min_length=1, max_length=100)
    payment_date: date
    method: str = Field(min_length=2, max_length=60)
    reference: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_payment(self) -> "PaymentCreate":
        credit_ids = [allocation.credit_id for allocation in self.allocations]
        if len(credit_ids) != len(set(credit_ids)):
            raise ValueError("Credits cannot be repeated")
        if self.payment_date > date.today():
            raise ValueError("Payment date cannot be in the future")
        return self


class PaymentRead(BaseModel):
    id: UUID
    code: str
    client_id: UUID
    client_name: str
    amount: Decimal
    credit_ids: list[UUID]
    credit_codes: list[str]
    credit_dates: list[date]
    payment_date: date
    method: str
    reference: str | None
    remaining_balance: Decimal
    registered_by: str
    created_at: datetime
