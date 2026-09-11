from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.client import Client
from app.models.commerce import Credit, CreditEvaluation
from app.models.settings import DEFAULT_ORGANIZATION_ID, SETTINGS_ID, BusinessSettings
from app.models.user import User, UserRole
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.schemas.finance import CreditProfileRead

router = APIRouter(prefix="/clients", tags=["clients"])
can_write = require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT)

DEFAULT_MAX_CREDIT_AMOUNT = Decimal("200")


@router.get("", response_model=list[ClientRead])
async def list_clients(
    search: str | None = Query(default=None, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Client]:
    statement = select(Client).where(Client.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Client.first_name.ilike(term),
                Client.last_name.ilike(term),
                Client.business_name.ilike(term),
                Client.document.ilike(term),
            )
        )
    statement = statement.order_by(Client.created_at.desc()).offset(offset).limit(limit)
    result = await db.scalars(statement)
    return list(result)


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Client:
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return client


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    _: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> Client:
    client = Client(**payload.model_dump(), organization_id=DEFAULT_ORGANIZATION_ID)
    db.add(client)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Documento ya registrado"
        ) from None
    await db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    _: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> Client:
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.commit()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_client(
    client_id: UUID,
    _: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> Response:
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    client.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _max_overdue_days(db: AsyncSession, client_id: UUID) -> int:
    due_dates = list(
        await db.scalars(
            select(Credit.due_date).where(
                Credit.client_id == client_id,
                Credit.pending_amount > 0,
                Credit.due_date < date.today(),
            )
        )
    )
    if not due_dates:
        return 0
    return max((date.today() - due).days for due in due_dates)


@router.get("/{client_id}/credit-profile", response_model=CreditProfileRead)
async def get_credit_profile(
    client_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreditProfileRead:
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    client_name = client.business_name or f"{client.first_name} {client.last_name}"
    latest = await db.scalar(
        select(CreditEvaluation)
        .where(CreditEvaluation.client_id == client.id)
        .order_by(CreditEvaluation.created_at.desc())
        .limit(1)
    )
    settings = await db.get(BusinessSettings, SETTINGS_ID)
    assigned_line = (
        latest.recommended_limit
        if latest
        else (settings.max_credit_amount if settings else DEFAULT_MAX_CREDIT_AMOUNT)
    )
    used = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
                Credit.client_id == client.id, Credit.pending_amount > 0
            )
        )
        or 0
    )
    available = max(Decimal("0"), assigned_line - used)
    utilization = float(used / assigned_line * 100) if assigned_line else 0.0
    overdue_condition = Credit.pending_amount > 0
    overdue_amount = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
                Credit.client_id == client.id,
                overdue_condition,
                Credit.due_date < date.today(),
            )
        )
        or 0
    )
    overdue_credits = int(
        await db.scalar(
            select(func.count(Credit.id)).where(
                Credit.client_id == client.id,
                overdue_condition,
                Credit.due_date < date.today(),
            )
        )
        or 0
    )
    active_credits = int(
        await db.scalar(
            select(func.count(Credit.id)).where(
                Credit.client_id == client.id, overdue_condition
            )
        )
        or 0
    )
    next_due_date = await db.scalar(
        select(func.min(Credit.due_date)).where(
            Credit.client_id == client.id,
            overdue_condition,
            Credit.due_date >= date.today(),
        )
    )
    return CreditProfileRead(
        client_id=client.id,
        client_name=client_name,
        assigned_line=assigned_line,
        used=used,
        available=available,
        utilization_percent=round(utilization, 2),
        last_score=latest.score if latest else None,
        last_risk=latest.risk if latest else None,
        last_evaluation_at=latest.created_at if latest else None,
        active_credits=active_credits,
        overdue_credits=overdue_credits,
        overdue_amount=overdue_amount,
        max_overdue_days=await _max_overdue_days(db, client.id),
        next_due_date=next_due_date,
    )
