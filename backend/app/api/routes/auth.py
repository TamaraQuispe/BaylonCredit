from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import AuditLog, RefreshToken, User
from app.schemas.user import (
    LogoutRequest,
    PasswordChange,
    ProfileUpdate,
    RefreshRequest,
    TokenResponse,
    UserRead,
)
from app.services.audit import add_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def new_session(db: AsyncSession, user: User) -> tuple[str, str, int]:
    access_token, expires_in = create_access_token(user.id, user.role.value)
    refresh_token, token_hash, expires_at = create_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    return access_token, refresh_token, expires_in


async def token_response(db: AsyncSession, user: User) -> TokenResponse:
    access_token, refresh_token, expires_in = new_session(db, user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    email = form.username.strip().lower()
    failed_since = datetime.now(UTC) - timedelta(minutes=settings.login_attempt_window_minutes)
    failed_attempts = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "login_failed",
            AuditLog.actor_email == email,
            AuditLog.created_at >= failed_since,
        )
    )
    if int(failed_attempts or 0) >= settings.login_attempt_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )

    user = await db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(form.password, user.hashed_password):
        add_audit_log(
            db,
            "login_failed",
            "session",
            actor_email=email,
            ip_address=request_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(UTC)
    response = await token_response(db, user)
    add_audit_log(db, "login_success", "session", actor=user, ip_address=request_ip(request))
    await db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    stored = await db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(payload.refresh_token))
        .with_for_update()
    )
    expires_at = stored.expires_at if stored else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if not stored or stored.revoked_at or not expires_at or expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user = await db.get(User, stored.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    stored.revoked_at = datetime.now(UTC)
    response = await token_response(db, user)
    await db.commit()
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> None:
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
    )
    if stored and not stored.revoked_at:
        stored.revoked_at = datetime.now(UTC)
        await db.commit()


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    add_audit_log(db, "profile_updated", "user", actor=current_user, entity_id=current_user.id)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )
    current_user.hashed_password = hash_password(payload.new_password)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    add_audit_log(db, "password_changed", "user", actor=current_user, entity_id=current_user.id)
    await db.commit()
