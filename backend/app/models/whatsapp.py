from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class NotificationStatus(StrEnum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class WhatsappNotification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "whatsapp_notifications"
    __table_args__ = (
        Index("ix_whatsapp_notifications_created_at", "created_at"),
    )

    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    template_name: Mapped[str] = mapped_column(String(60), nullable=False)
    evaluation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("credit_evaluations.id", ondelete="SET NULL"), index=True
    )
    credit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("credits.id", ondelete="SET NULL"), index=True
    )
    message_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="whatsapp_notification_status", native_enum=False),
        default=NotificationStatus.SENT,
        server_default="sent",
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text)