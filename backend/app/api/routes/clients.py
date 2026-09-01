from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User, UserRole
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])
can_write = require_roles(UserRole.ADMIN, UserRole.OPERATOR)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    _: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> Client:
    client = Client(**payload.model_dump())
    db.add(client)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Document already registered"
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    client.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
