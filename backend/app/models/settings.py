from decimal import Decimal
from uuid import UUID

from sqlalchemy import UUID as SqlUuid
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

SETTINGS_ID = UUID("00000000-0000-0000-0000-0000000000c0")


class BusinessSettings(TimestampMixin, Base):
    __tablename__ = "business_settings"

    id: Mapped[UUID] = mapped_column(SqlUuid(as_uuid=True), primary_key=True, default=SETTINGS_ID)
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    business_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    business_address: Mapped[str] = mapped_column(String(255), nullable=False)
    default_credit_term_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    max_credit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=200, nullable=False)
    due_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )