import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: UUID, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    token = jwt.encode(
        {"sub": str(user_id), "role": role, "exp": expires_at, "iat": datetime.now(UTC)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    subject = payload.get("sub")
    if not subject:
        raise jwt.InvalidTokenError("Token subject is missing")
    return UUID(subject)


def create_refresh_token() -> tuple[str, str, datetime]:
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return token, hash_token(token), expires_at


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
