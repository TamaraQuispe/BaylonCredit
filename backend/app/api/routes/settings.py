from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.settings import DEFAULT_ORGANIZATION_ID, SETTINGS_ID, BusinessSettings, Organization
from app.models.user import User, UserRole
from app.schemas.settings import CompanyRead, CompanyUpdate, SettingsRead, SettingsUpdate
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
    "scoring_low_min": 80,
    "scoring_medium_min": 60,
    "scoring_min_approved": 60,
    "overdue_grace_days": 0,
    "overdue_block_days": 30,
    "max_exposure_percent": 80,
    "new_client_blocked_days": 0,
    "reminder_days_before": 3,
    "reminder_send_on_due_day": False,
    "reminder_send_after_overdue": False,
}


async def get_organization(db: AsyncSession) -> Organization:
    organization = await db.get(Organization, DEFAULT_ORGANIZATION_ID)
    if organization:
        return organization
    organization = Organization(
        id=DEFAULT_ORGANIZATION_ID,
        name="Cervecería Baylón",
        phone="+51 987 654 321",
        address="Av. Principal 123, Lima, Perú",
        is_active=True,
    )
    db.add(organization)
    await db.commit()
    return organization


async def get_settings_record(db: AsyncSession, actor: User | None = None) -> BusinessSettings:
    settings = await db.get(BusinessSettings, SETTINGS_ID)
    if settings:
        return settings
    settings = BusinessSettings(
        id=SETTINGS_ID,
        organization_id=DEFAULT_ORGANIZATION_ID,
        **DEFAULT_SETTINGS,
        updated_by_id=actor.id if actor else None,
    )
    db.add(settings)
    await db.commit()
    return settings


def serialize_settings(
    settings: BusinessSettings, organization: Organization | None
) -> SettingsRead:
    data = SettingsRead.model_validate(settings, from_attributes=True)
    return data.model_copy(
        update={"organization": CompanyRead.model_validate(organization) if organization else None}
    )


@router.get("", response_model=SettingsRead)
async def read_settings(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsRead:
    settings = await get_settings_record(db)
    organization = await db.get(Organization, settings.organization_id)
    return serialize_settings(settings, organization)


@router.patch("", response_model=SettingsRead)
async def update_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> SettingsRead:
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
    organization = await db.get(Organization, settings.organization_id)
    return serialize_settings(settings, organization)


@router.patch("/company", response_model=CompanyRead)
async def update_company(
    payload: CompanyUpdate,
    current_user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    organization = await get_organization(db)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(organization, field, value)
    add_audit_log(
        db,
        "company_updated",
        "organization",
        actor=current_user,
        entity_id=organization.id,
        details={key: str(value) if value is not None else None for key, value in changes.items()},
    )
    await db.commit()
    await db.refresh(organization)
    return organization