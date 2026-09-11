"""Webhooks and management endpoints for the WhatsApp integration.

The webhook endpoints are public by design because Meta calls them with
no authentication; the POST one is protected by the ``X-Hub-Signature-256``
header derived from ``WHATSAPP_APP_SECRET`` when configured.
"""

from __future__ import annotations

import json
import logging
from hmac import compare_digest
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.whatsapp import NotificationStatus, WhatsappNotification
from app.schemas.whatsapp import WhatsappNotificationRead
from app.services.whatsapp import send_credit_reminder, send_due_reminders, verify_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
console = require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.COLLECTIONS)
admin_only = require_roles(UserRole.ADMIN)

_STATUS_MAP = {
    "sent": NotificationStatus.SENT,
    "delivered": NotificationStatus.DELIVERED,
    "read": NotificationStatus.READ,
    "failed": NotificationStatus.FAILED,
}


@router.get("/webhook")
async def webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    settings = get_settings()
    valid_token = bool(settings.whatsapp_verify_token) and hub_verify_token is not None
    if hub_mode == "subscribe" and valid_token and compare_digest(
        settings.whatsapp_verify_token, hub_verify_token
    ):
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verification token")


@router.post("/webhook")
async def webhook_events(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    settings = get_settings()
    body = await request.body()
    if settings.whatsapp_app_secret and not verify_signature(
        settings.whatsapp_app_secret, request.headers.get("x-hub-signature-256"), body
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    await _process_events(db, json.loads(body))
    return {"status": "ok"}


async def _process_events(db: AsyncSession, payload: dict) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status_event in value.get("statuses", []):
                message_id = status_event.get("id")
                delivery = _STATUS_MAP.get(status_event.get("status", ""))
                if not message_id or delivery is None:
                    continue
                result = await db.execute(
                    update(WhatsappNotification)
                    .where(WhatsappNotification.message_id == message_id)
                    .values(status=delivery)
                )
                if result.rowcount:
                    logger.info("WhatsApp message %s %s", message_id, delivery)
            for message in value.get("messages", []):
                logger.info("Ignored inbound WhatsApp message from %s", message.get("from", ""))
    await db.commit()


@router.post("/reminders")
async def trigger_reminders(_: User = Depends(console)) -> dict[str, int]:
    settings = get_settings()
    if not (settings.whatsapp_enabled and settings.whatsapp_notify_reminders):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="WhatsApp reminders are not enabled",
        )
    return await send_due_reminders()


@router.post("/reminders/{credit_id}")
async def trigger_single_reminder(
    credit_id: UUID,
    _: User = Depends(console),
) -> dict[str, int]:
    settings = get_settings()
    if not (settings.whatsapp_enabled and settings.whatsapp_notify_reminders):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Los recordatorios de WhatsApp no están habilitados",
        )
    return await send_credit_reminder(credit_id)


@router.get("/notifications", response_model=list[WhatsappNotificationRead])
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> list[WhatsappNotification]:
    return list(
        await db.scalars(
            select(WhatsappNotification)
            .order_by(WhatsappNotification.created_at.desc())
            .limit(limit)
        )
    )