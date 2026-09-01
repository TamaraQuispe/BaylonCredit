from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.commerce import InventoryMovementType, PaymentMode, RiskLevel


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=80)
    icon: str = Field(default="category", max_length=60)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit_cost: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    icon: str | None = Field(default=None, max_length=60)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    minimum_stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StockChange(BaseModel):
    movement_type: InventoryMovementType
    quantity: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_movement(self) -> "StockChange":
        if self.movement_type == InventoryMovementType.ENTRY and self.quantity == 0:
            raise ValueError("An inventory entry must be greater than zero")
        if self.movement_type == InventoryMovementType.SALE:
            raise ValueError("Sale movements can only be created by the sales endpoint")
        return self


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=10_000)


class SaleCreate(BaseModel):
    payment_mode: PaymentMode
    client_id: UUID | None = None
    due_date: date | None = None
    items: list[SaleItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_credit_data(self) -> "SaleCreate":
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Products cannot be repeated")
        if self.payment_mode == PaymentMode.CREDIT and (not self.client_id or not self.due_date):
            raise ValueError("Credit sales require client_id and due_date")
        if self.payment_mode == PaymentMode.CASH and (self.client_id or self.due_date):
            raise ValueError("Cash sales cannot include credit data")
        return self


class SaleItemRead(BaseModel):
    product_id: UUID
    product_name: str
    product_category: str
    unit_price: Decimal
    quantity: int
    line_subtotal: Decimal


class CreditRead(BaseModel):
    id: UUID
    code: str
    client_id: UUID
    original_amount: Decimal
    pending_amount: Decimal
    due_date: date
    status: str
    risk: RiskLevel
    score: int
    recommended_limit: Decimal


class SaleRead(BaseModel):
    id: UUID
    code: str
    payment_mode: PaymentMode
    client_id: UUID | None
    client_name: str | None
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    created_at: datetime
    items: list[SaleItemRead]
    credit: CreditRead | None = None
