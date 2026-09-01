from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_roles(UserRole.ADMIN)


@router.get("", response_model=list[UserRead], dependencies=[Depends(admin_only)])
async def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    statement = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.scalars(statement)
    return list(result)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = User(
        email=str(payload.email).lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from None
    await db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=UserRead)
async def change_user_status(
    user_id: UUID,
    active: bool,
    current_user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id and not active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot disable your own account",
        )
    user.is_active = active
    await db.commit()
    await db.refresh(user)
    return user
