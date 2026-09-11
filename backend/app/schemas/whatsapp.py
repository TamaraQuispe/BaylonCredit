from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.whatsapp import NotificationStatus


class WhatsappNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone: str
    template_name: str
    evaluation_id: UUID | None
    credit_id: UUID | None
    message_id: str | None
    status: NotificationStatus
    error: str | None
    created_at: datetime