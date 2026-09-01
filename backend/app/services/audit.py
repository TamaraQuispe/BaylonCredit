from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog, User


def add_audit_log(
    db: AsyncSession,
    action: str,
    entity_type: str,
    *,
    actor: User | None = None,
    actor_email: str | None = None,
    entity_id: UUID | str | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
    description: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        ip_address=ip_address,
        details=details,
        description=description,
    )
    db.add(entry)
    return entry
