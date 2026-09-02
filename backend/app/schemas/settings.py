from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_name: str
    business_phone: str
    business_address: str
    default_credit_term_days: int = Field(ge=1, le=90)
    max_credit_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_alerts_enabled: bool


class SettingsUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    business_phone: str | None = Field(default=None, min_length=3, max_length=30)
    business_address: str | None = Field(default=None, min_length=3, max_length=255)
    default_credit_term_days: int | None = Field(default=None, ge=1, le=90)
    max_credit_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    due_alerts_enabled: bool | None = None