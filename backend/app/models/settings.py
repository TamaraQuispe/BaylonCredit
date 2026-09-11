from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import UUID as SqlUuid
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy import Boolean as SqlBool
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

SETTINGS_ID = UUID("00000000-0000-0000-0000-0000000000c0")
DEFAULT_ORGANIZATION_ID = UUID("00000000-0000-0000-0000-0000000000d0")


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(SqlUuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    ruc: Mapped[str | None] = mapped_column(String(11))
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BusinessSettings(TimestampMixin, Base):
    __tablename__ = "business_settings"

    id: Mapped[UUID] = mapped_column(SqlUuid(as_uuid=True), primary_key=True, default=SETTINGS_ID)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL")
    )
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    business_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    business_address: Mapped[str] = mapped_column(String(255), nullable=False)
    default_credit_term_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    max_credit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=200, nullable=False)
    due_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scoring_low_min: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    scoring_medium_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    scoring_min_approved: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    overdue_grace_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overdue_block_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_exposure_percent: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    new_client_blocked_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reminder_days_before: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    reminder_send_on_due_day: Mapped[bool] = mapped_column(SqlBool, default=False, nullable=False)
    reminder_send_after_overdue: Mapped[bool] = mapped_column(
        SqlBool, default=False, nullable=False
    )
    updated_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )