"""WhatsApp Business API client and notification dispatch.

Integrates with the Meta Graph API to send template messages and to
receive webhook events. All behaviour is gated by ``whatsapp_enabled``
and the per-feature flags (evaluations, reminders) so the system keeps
working in dry-run mode until the production credentials are provided.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import re
from datetime import UTC, date, datetime, timedelta
from hmac import compare_digest
from uuid import UUID

import httpx
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.client import Client
from app.models.commerce import Credit, CreditEvaluation, CreditStatus
from app.models.whatsapp import NotificationStatus, WhatsappNotification

logger = logging.getLogger(__name__)

_GRAPH_MESSAGES_URL = "{base}/{version}/{phone_number_id}/messages"
_PHONE_DIGITS = re.compile(r"\D+")


class WhatsAppError(RuntimeError):
    pass


def normalize_phone(phone: str, default_country_code: str = "51") -> str:
    """Return an E.164 number.

    Accepts local ``9XXXXXXXX`` form, an international number without the
    leading ``+`` and an already international ``+51...`` number.
    """
    raw = phone.strip()
    if raw.startswith("+"):
        return "+" + _PHONE_DIGITS.sub("", raw)
    digits = _PHONE_DIGITS.sub("", raw)
    if (
        len(default_country_code) == 2
        and digits.startswith(default_country_code)
        and len(digits) == 9 + len(default_country_code)
    ):
        return "+" + digits
    if digits.startswith("9") and len(digits) == 9:
        return "+" + default_country_code + digits
    return "+" + digits


def compute_signature(secret: str, body: bytes | str) -> str:
    payload = body if isinstance(body, bytes) else body.encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, header: str | None, body: bytes | str) -> bool:
    return bool(header) and compare_digest(compute_signature(secret, body), header)


def build_template_payload(
    to: str,
    template_name: str,
    body_values: list[str],
    *,
    language: str = "es",
) -> dict:
    components: list[dict] = []
    if body_values:
        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": value} for value in body_values],
            }
        )
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "recipient_type": "individual",
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components,
        },
    }


def evaluation_body_values(client_name: str, evaluation: CreditEvaluation) -> list[str]:
    verdict = "aprobada" if evaluation.approved else "rechazada"
    return [client_name, verdict, f"{evaluation.recommended_limit:.2f}"]


def reminder_body_values(client_name: str, credit: Credit) -> list[str]:
    overdue = credit.due_date < date.today()
    event = "se venció" if overdue else "vence"
    return [
        client_name,
        f"{credit.original_amount:.2f}",
        event,
        credit.due_date.isoformat(),
        f"{credit.pending_amount:.2f}",
    ]


async def send_template_message(
    phone: str,
    template_name: str,
    body_values: list[str],
    *,
    language: str = "es",
) -> str:
    settings = get_settings()
    to = normalize_phone(phone, settings.whatsapp_default_country_code)
    if not settings.whatsapp_enabled:
        logger.info("WhatsApp disabled; skipping template=%s to=%s", template_name, to)
        return "mock"
    payload = build_template_payload(to, template_name, body_values, language=language)
    url = _GRAPH_MESSAGES_URL.format(
        base=settings.whatsapp_graph_base_url,
        version=settings.whatsapp_api_version,
        phone_number_id=settings.whatsapp_phone_number_id,
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    async with httpx.AsyncClient(timeout=settings.whatsapp_timeout_seconds) as client:
        response = await client.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise WhatsAppError(f"Graph API responded {response.status_code}: {response.text[:300]}")
    data = response.json()
    message_id = (data.get("messages") or [{}])[0].get("id", "")
    logger.info("WhatsApp template=%s sent to=%s message_id=%s", template_name, to, message_id)
    return message_id


def enqueue_evaluation_notification(
    background_tasks: BackgroundTasks, evaluation_id: UUID
) -> None:
    settings = get_settings()
    if settings.whatsapp_enabled and settings.whatsapp_notify_evaluations:
        background_tasks.add_task(dispatch_evaluation_notification, evaluation_id)


async def dispatch_evaluation_notification(evaluation_id: UUID) -> None:
    settings = get_settings()
    if not (settings.whatsapp_enabled and settings.whatsapp_notify_evaluations):
        return
    try:
        async with SessionFactory() as db:
            evaluation = await db.get(CreditEvaluation, evaluation_id)
            if evaluation is None:
                return
            client = await db.get(Client, evaluation.client_id)
            if client is None or not client.phone:
                return
            client_name = client.business_name or f"{client.first_name} {client.last_name}"
            notification = await _send_and_record(
                db,
                template_name=settings.whatsapp_template_evaluation,
                body_values=evaluation_body_values(client_name, evaluation),
                phone=client.phone,
                evaluation_id=evaluation.id,
            )
            db.add(notification)
            await db.commit()
    except Exception:
        logger.exception("Failed to dispatch evaluation notification %s", evaluation_id)


async def _send_and_record(
    db: AsyncSession,
    *,
    template_name: str,
    body_values: list[str],
    phone: str,
    evaluation_id: UUID | None = None,
    credit_id: UUID | None = None,
) -> WhatsappNotification:
    try:
        message_id = await send_template_message(phone, template_name, body_values)
        return WhatsappNotification(
            phone=phone,
            template_name=template_name,
            evaluation_id=evaluation_id,
            credit_id=credit_id,
            message_id=message_id,
            status=NotificationStatus.SENT,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("WhatsApp template=%s to=%s failed: %s", template_name, phone, exc)
        return WhatsappNotification(
            phone=phone,
            template_name=template_name,
            evaluation_id=evaluation_id,
            credit_id=credit_id,
            status=NotificationStatus.FAILED,
            error=str(exc),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def collect_due_credits(db: AsyncSession) -> list[tuple[Credit, Client]]:
    settings = get_settings()
    horizon = date.today() + timedelta(days=settings.whatsapp_reminder_days_before)
    rows = (
        await db.execute(
            select(Credit, Client)
            .join(Client, Client.id == Credit.client_id)
            .where(
                Credit.pending_amount > 0,
                Credit.due_date <= horizon,
                Credit.status != CreditStatus.PAID,
            )
        )
    ).all()
    return [(credit, client) for credit, client in rows]


async def _already_notified(
    db: AsyncSession, credit_id: UUID, window: timedelta
) -> bool:
    cutoff = datetime.now(UTC) - window
    notifications = list(
        await db.scalars(
            select(WhatsappNotification)
            .where(
                WhatsappNotification.credit_id == credit_id,
                WhatsappNotification.status != NotificationStatus.FAILED,
            )
            .order_by(WhatsappNotification.created_at.desc())
            .limit(1)
        )
    )
    if not notifications:
        return False
    last = notifications[0]
    return _as_utc(last.created_at) >= cutoff


async def send_due_reminders(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> dict[str, int]:
    settings = get_settings()
    sent = 0
    skipped = 0
    failed = 0
    window = timedelta(hours=settings.whatsapp_reminder_interval_hours)
    factory = session_factory or SessionFactory
    async with factory() as db:
        for credit, client in await collect_due_credits(db):
            if await _already_notified(db, credit.id, window):
                skipped += 1
                continue
            client_name = client.business_name or f"{client.first_name} {client.last_name}"
            notification = await _send_and_record(
                db,
                template_name=settings.whatsapp_template_reminder,
                body_values=reminder_body_values(client_name, credit),
                phone=client.phone,
                credit_id=credit.id,
            )
            db.add(notification)
            if notification.status is NotificationStatus.FAILED:
                failed += 1
            else:
                sent += 1
        await db.commit()
    logger.info("WhatsApp due reminders sent=%s skipped=%s failed=%s", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}


async def reminder_loop(interval_hours: int) -> None:
    while True:
        await asyncio.sleep(interval_hours * 3600)
        try:
            await send_due_reminders()
        except Exception:  # noqa: BLE001
            logger.exception("Due reminder cycle failed")