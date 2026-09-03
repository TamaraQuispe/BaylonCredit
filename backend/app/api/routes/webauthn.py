from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn.helpers.exceptions import WebAuthnException

from app.api.dependencies import get_current_user
from app.api.routes.auth import token_response
from app.db.session import get_db
from app.models.user import User, WebauthnCredential
from app.schemas.user import (
    WebauthnAuthenticationBegin,
    WebauthnAuthenticationBeginResponse,
    WebauthnAuthenticationFinish,
    WebauthnCredentialRead,
    WebauthnRegistrationBegin,
    WebauthnRegistrationBeginResponse,
    WebauthnRegistrationFinish,
)
from app.services import webauthn
from app.services.audit import add_audit_log

router = APIRouter(prefix="/auth/webauthn", tags=["webauthn"])


def decode_user_handle(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


async def available_credential_ids(db: AsyncSession, user_id: UUID) -> list[str]:
    rows = await db.scalars(
        select(WebauthnCredential.credential_id).where(WebauthnCredential.user_id == user_id)
    )
    return list(rows.all())


# ---------------------------------------------------------------- registration


@router.post(
    "/registration/begin",
    response_model=WebauthnRegistrationBeginResponse,
    status_code=status.HTTP_200_OK,
)
async def registration_begin(
    payload: WebauthnRegistrationBegin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebauthnRegistrationBeginResponse:
    existing = await available_credential_ids(db, current_user.id)
    result = webauthn.build_registration_options(
        user_id=current_user.id,
        user_name=current_user.email,
        existing_credential_ids=existing,
    )
    return WebauthnRegistrationBeginResponse(**result)


@router.post("/registration/finish", status_code=status.HTTP_201_CREATED)
async def registration_finish(
    payload: WebauthnRegistrationFinish,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebauthnCredentialRead:
    try:
        verified = webauthn.verify_registration(
            session_id=payload.session_id,
            challenge=payload.challenge,
            credential=payload.credential,
            name=payload.name,
        )
    except WebAuthnException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from None

    existing = await db.scalar(
        select(WebauthnCredential).where(
            WebauthnCredential.user_id == current_user.id,
            WebauthnCredential.credential_id == verified["credential_id"],
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This security key is already registered."
        )

    credential = WebauthnCredential(
        user_id=current_user.id,
        credential_id=verified["credential_id"],
        credential_public_key=verified["credential_public_key"],
        sign_count=verified["sign_count"],
        device_type=verified["credential_device_type"],
        backed_up=verified["credential_backed_up"],
        transports=",".join(str(t) for t in verified["transports"]) or None,
        name=verified["name"],
    )
    db.add(credential)
    add_audit_log(
        db,
        "webauthn_registered",
        "user",
        actor=current_user,
        entity_id=current_user.id,
        details={"credential_id": verified["credential_id"]},
    )
    await db.commit()
    await db.refresh(credential)
    return WebauthnCredentialRead.model_validate(credential)


@router.get("/credentials", response_model=list[WebauthnCredentialRead])
async def list_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WebauthnCredentialRead]:
    rows = (
        await db.scalars(
            select(WebauthnCredential)
            .where(WebauthnCredential.user_id == current_user.id)
            .order_by(WebauthnCredential.created_at)
        )
    ).all()
    return [WebauthnCredentialRead.model_validate(row) for row in rows]


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    credential = await db.scalar(
        select(WebauthnCredential).where(
            WebauthnCredential.user_id == current_user.id,
            WebauthnCredential.credential_id == credential_id,
        )
    )
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    await db.delete(credential)
    add_audit_log(
        db,
        "webauthn_removed",
        "user",
        actor=current_user,
        entity_id=current_user.id,
        details={"credential_id": credential_id},
    )
    await db.commit()


# ---------------------------------------------------------------- authentication


@router.post(
    "/authentication/begin",
    response_model=WebauthnAuthenticationBeginResponse,
)
async def authentication_begin(
    payload: WebauthnAuthenticationBegin,
    db: AsyncSession = Depends(get_db),
) -> WebauthnAuthenticationBeginResponse:
    user = None
    if payload.user_handle:
        user_id = decode_user_handle(payload.user_handle)
        if user_id:
            user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No valid account found"
            )

    allow_ids: list[str] = []
    if user:
        allow_ids = await available_credential_ids(db, user.id)

    result = webauthn.build_authentication_options(allow_credential_ids=allow_ids)
    return WebauthnAuthenticationBeginResponse(**result)


@router.post(
    "/authentication/finish",
    response_model=dict,
)
async def authentication_finish(
    payload: WebauthnAuthenticationFinish,
    db: AsyncSession = Depends(get_db),
) -> dict:
    credential_id = payload.credential.get("id", "")
    credential = await db.scalar(
        select(WebauthnCredential).where(WebauthnCredential.credential_id == credential_id)
    )
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown credential")

    user = await db.get(User, credential.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

    handle = decode_user_handle(payload.user_handle or "")
    if handle and handle != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Credential/user mismatch"
        )

    try:
        new_count, device_type, backed_up = webauthn.verify_authentication(
            session_id=payload.session_id,
            challenge=payload.challenge,
            credential=payload.credential,
            credential_public_key=credential.credential_public_key,
            sign_count=credential.sign_count,
        )
    except WebAuthnException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from None

    credential.sign_count = new_count
    credential.device_type = device_type
    credential.backed_up = backed_up
    await db.commit()
    add_audit_log(
        db,
        "webauthn_login_success",
        "session",
        actor=user,
        details={"credential_id": credential_id},
    )
    await db.commit()

    response = await token_response(db, user)
    return {
        "access_token": response.access_token,
        "refresh_token": response.refresh_token,
        "token_type": response.token_type,
        "expires_in": response.expires_in,
        "user": response.user,
    }