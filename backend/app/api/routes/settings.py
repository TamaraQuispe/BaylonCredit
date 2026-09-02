from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.settings import SETTINGS_ID, BusinessSettings
from app.models.user import User, UserRole
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.services.audit import add_audit_log

router = APIRouter(prefix="/settings", tags=["settings"])
admin_only = require_roles(UserRole.ADMIN)

DEFAULT_SETTINGS = {
    "business_name": "Cervecería Baylón",
    "business_phone": "+51 987 654 321",
    "business_address": "Av. Principal 123, Lima, Perú",
    "default_credit_term_days": 15,
    "max_credit_amount": 200,
    "due_alerts_enabled": True,
}


async def get_settings_record(db: AsyncSession, actor: User | None = None) -> BusinessSettings:
    settings = await db.get(BusinessSettings, SETTINGS_ID)
    if settings:
        return settings
    settings = BusinessSettings(
        id=SETTINGS_ID,
        **DEFAULT_SETTINGS,
        updated_by_id=actor.id if actor else None,
    )
    db.add(settings)
    await db.commit()
    return settings


@router.get("", response_model=SettingsRead)
async def read_settings(
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> BusinessSettings:
    return await get_settings_record(db)


@router.patch("", response_model=SettingsRead)
async def update_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> BusinessSettings:
    settings = await get_settings_record(db, current_user)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(settings, field, value)
    settings.updated_by_id = current_user.id
    add_audit_log(
        db,
        "settings_updated",
        "settings",
        actor=current_user,
        entity_id=settings.id,
        details={key: str(value) if value is not None else None for key, value in changes.items()},
    )
    await db.commit()
    await db.refresh(settings)
    return settings