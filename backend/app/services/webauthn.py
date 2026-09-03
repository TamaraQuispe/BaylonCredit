"""Server-side WebAuthn (FIDO2) ceremonies using py_webauthn.

Challenges are stored in-memory keyed by a random token tied to the pending
ceremony. This is sufficient for a single-instance deployment; for multi-worker
deployments an external cache (e.g. Redis) should back this state.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from secrets import token_urlsafe
from uuid import UUID

from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url, options_to_json
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.config import get_settings

CHALLENGE_TTL_SECONDS = 300
MAX_PENDING = 100


@dataclass
class PendingChallenge:
    challenge: bytes
    user_id: UUID | None
    user_name: str
    credential_id: str | None
    expires_at: float


_pending: dict[str, PendingChallenge] = {}


def _prune() -> None:
    now = time.time()
    expired = [token for token, entry in _pending.items() if entry.expires_at <= now]
    for token in expired:
        _pending.pop(token, None)
    if len(_pending) > MAX_PENDING:
        overflow = sorted(_pending, key=lambda t: _pending[t].expires_at)[: -MAX_PENDING]
        for token in overflow:
            _pending.pop(token, None)


def _store(challenge: bytes, *, user_id: UUID | None, user_name: str) -> str:
    _prune()
    token = token_urlsafe(32)
    _pending[token] = PendingChallenge(
        challenge=challenge,
        user_id=user_id,
        user_name=user_name,
        credential_id=None,
        expires_at=time.time() + CHALLENGE_TTL_SECONDS,
    )
    return token


def _consume_by_token(token: str, *expected_challenge: bytes) -> PendingChallenge:
    entry = _pending.pop(token, None)
    if not entry or entry.expires_at <= time.time():
        raise WebAuthnException("WebAuthn session is missing or has expired. Please try again.")
    if expected_challenge and entry.challenge != expected_challenge[0]:
        raise WebAuthnException("WebAuthn challenge mismatch. Please try again.")
    return entry


def _descriptor(credential_id: str) -> PublicKeyCredentialDescriptor:
    return PublicKeyCredentialDescriptor(id=base64url_to_bytes(credential_id))


def build_registration_options(
    *,
    user_id: UUID,
    user_name: str,
    existing_credential_ids: list[str],
) -> dict:
    settings = get_settings()
    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=str(user_id).encode(),
        user_name=user_name,
        exclude_credentials=[_descriptor(cid) for cid in existing_credential_ids],
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
        timeout=120000,
    )
    token = _store(options.challenge, user_id=user_id, user_name=user_name)
    return {
        "session_id": token,
        "options": json.loads(options_to_json(options)),
    }


def verify_registration(
    *,
    session_id: str,
    challenge: str,
    credential: dict,
    name: str | None,
) -> dict:
    settings = get_settings()
    entry = _consume_by_token(session_id, base64url_to_bytes(challenge))
    if entry.user_id is None:
        raise WebAuthnException("Registration requires an authenticated user.")
    verification = verify_registration_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(challenge),
        expected_rp_id=settings.webauthn_rp_id,
        expected_origin=settings.webauthn_origin,
        require_user_verification=True,
    )
    transports = credential.get("response", {}).get("transports", [])
    return {
        "credential_id": bytes_to_base64url(verification.credential_id),
        "credential_public_key": bytes_to_base64url(verification.credential_public_key),
        "sign_count": verification.sign_count,
        "credential_device_type": verification.credential_device_type,
        "credential_backed_up": verification.credential_backed_up,
        "transports": transports,
        "name": name,
    }


def build_authentication_options(
    *,
    allow_credential_ids: list[str],
) -> dict:
    settings = get_settings()
    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        timeout=120000,
        user_verification=UserVerificationRequirement.PREFERRED,
        allow_credentials=[_descriptor(cid) for cid in allow_credential_ids],
    )
    token = _store(options.challenge, user_id=None, user_name="BaylonCredit")
    return {
        "session_id": token,
        "options": json.loads(options_to_json(options)),
    }


def verify_authentication(
    *,
    session_id: str,
    challenge: str,
    credential: dict,
    credential_public_key: str,
    sign_count: int,
) -> tuple[int, str, bool]:
    settings = get_settings()
    _consume_by_token(session_id, base64url_to_bytes(challenge))
    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(challenge),
        expected_rp_id=settings.webauthn_rp_id,
        expected_origin=settings.webauthn_origin,
        credential_public_key=base64url_to_bytes(credential_public_key),
        credential_current_sign_count=sign_count,
        require_user_verification=True,
    )
    return (
        verification.new_sign_count,
        verification.credential_device_type,
        verification.credential_backed_up,
    )