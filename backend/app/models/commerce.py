from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class PaymentMode(StrEnum):
    CASH = "contado"
    CREDIT = "fiado"


class InventoryMovementType(StrEnum):
    ENTRY = "entrada"
    ADJUSTMENT = "ajuste"
    SALE = "venta"


class CreditStatus(StrEnum):
    CURRENT = "al-dia"
    OVERDUE = "vencido"
    PAID = "pagado"


class RiskLevel(StrEnum):
    VERY_LOW = "muy-bajo"
    LOW = "bajo"
    MEDIUM = "medio"
    HIGH = "alto"
    CRITICAL = "critico"


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="category", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Sale(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales"

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    payment_mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, name="payment_mode", native_enum=False), nullable=False
    )
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"))
    client_name: Mapped[str | None] = mapped_column(String(160))
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class SaleItem(UUIDMixin, Base):
    __tablename__ = "sale_items"

    sale_id: Mapped[UUID] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    product_category: Mapped[str] = mapped_column(String(80), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class Credit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "credits"

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), index=True
    )
    sale_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"), unique=True
    )
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pending_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    credit_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[CreditStatus] = mapped_column(
        Enum(CreditStatus, name="credit_status", native_enum=False),
        default=CreditStatus.CURRENT,
        nullable=False,
    )
    risk: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level", native_enum=False), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class InventoryMovement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "inventory_movements"

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        Enum(InventoryMovementType, name="inventory_movement_type", native_enum=False),
        nullable=False,
    )
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[UUID | None]
    note: Mapped[str | None] = mapped_column(String(255))
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), index=True
    )
    client_name: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str] = mapped_column(String(60), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    registered_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class PaymentAllocation(UUIDMixin, Base):
    __tablename__ = "payment_allocations"

    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    credit_id: Mapped[UUID] = mapped_column(
        ForeignKey("credits.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
