from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    ruc: str | None
    phone: str | None
    address: str | None
    logo_url: str | None


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    ruc: str | None = Field(default=None, pattern=r"^\d{11}$")
    phone: str | None = Field(default=None, min_length=3, max_length=30)
    address: str | None = Field(default=None, min_length=3, max_length=255)
    logo_url: str | None = Field(default=None, max_length=2048)


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization: CompanyRead | None = None
    business_name: str
    business_phone: str
    business_address: str
    default_credit_term_days: int = Field(ge=1, le=90)
    max_credit_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_alerts_enabled: bool
    scoring_low_min: int = Field(ge=1, le=100)
    scoring_medium_min: int = Field(ge=1, le=100)
    scoring_min_approved: int = Field(ge=1, le=100)
    overdue_grace_days: int = Field(ge=0, le=90)
    overdue_block_days: int = Field(ge=0, le=365)
    max_exposure_percent: int = Field(ge=1, le=100)
    new_client_blocked_days: int = Field(ge=0, le=365)
    reminder_days_before: int = Field(ge=0, le=30)
    reminder_send_on_due_day: bool
    reminder_send_after_overdue: bool


class SettingsUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    business_phone: str | None = Field(default=None, min_length=3, max_length=30)
    business_address: str | None = Field(default=None, min_length=3, max_length=255)
    default_credit_term_days: int | None = Field(default=None, ge=1, le=90)
    max_credit_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    due_alerts_enabled: bool | None = None
    scoring_low_min: int | None = Field(default=None, ge=1, le=100)
    scoring_medium_min: int | None = Field(default=None, ge=1, le=100)
    scoring_min_approved: int | None = Field(default=None, ge=1, le=100)
    overdue_grace_days: int | None = Field(default=None, ge=0, le=90)
    overdue_block_days: int | None = Field(default=None, ge=0, le=365)
    max_exposure_percent: int | None = Field(default=None, ge=1, le=100)
    new_client_blocked_days: int | None = Field(default=None, ge=0, le=365)
    reminder_days_before: int | None = Field(default=None, ge=0, le=30)
    reminder_send_on_due_day: bool | None = None
    reminder_send_after_overdue: bool | None = None