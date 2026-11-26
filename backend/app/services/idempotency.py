"""Idempotencia persistente para operaciones de escritura (P0-03 de la guia).

Contrato:
- Sin cabecera ``Idempotency-Key`` la ruta se comporta como siempre.
- Con clave nueva: la operacion se ejecuta una sola vez.
- Con la misma clave y el mismo payload ya completada: se devuelve la misma
  respuesta guardada, sin repetir la escritura.
- Con la misma clave y otro payload: 409.
- Con la misma clave todavia en curso: 409 (no se reintenta la escritura).

La fila de idempotencia se confirma en la misma transaccion que el recurso, asi
que un commit perdido no deja ni recurso ni clave completada.
"""

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey

HEADER_NAME = "Idempotency-Key"
MAX_KEY_LENGTH = 120
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


@dataclass(frozen=True)
class IdempotentStart:
    """Resultado de reservar la clave.

    ``record`` es la fila a completar al terminar; si ``replay_body`` viene con
    datos, la operacion ya se ejecuto antes y debe devolverse tal cual.
    """

    record: IdempotencyKey | None = None
    replay_status: int | None = None
    replay_body: dict | None = None


def normalize_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = raw.strip()
    if not key:
        return None
    if len(key) > MAX_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "La cabecera Idempotency-Key no puede superar "
                f"{MAX_KEY_LENGTH} caracteres."
            ),
        )
    return key


def request_fingerprint(scope: str, payload: dict) -> str:
    canonical = json.dumps(
        {"scope": scope, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _find(
    db: AsyncSession, key: str, user_id: UUID, scope: str
) -> IdempotencyKey | None:
    return await db.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.key == key,
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.scope == scope,
        )
    )


def _resolve(existing: IdempotencyKey, fingerprint: str) -> IdempotentStart:
    if existing.request_hash != fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La clave de idempotencia ya se uso con otra solicitud.",
        )
    if existing.status == STATUS_COMPLETED and existing.response_body is not None:
        return IdempotentStart(
            replay_status=existing.response_status or status.HTTP_200_OK,
            replay_body=existing.response_body,
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="La solicitud con esta clave sigue en proceso; reintenta mas tarde.",
    )


async def begin(
    db: AsyncSession,
    *,
    key: str | None,
    scope: str,
    user_id: UUID,
    payload: dict,
) -> IdempotentStart:
    """Reserva la clave o devuelve la respuesta ya guardada."""
    if key is None:
        return IdempotentStart()
    fingerprint = request_fingerprint(scope, payload)
    existing = await _find(db, key, user_id, scope)
    if existing is not None:
        return _resolve(existing, fingerprint)

    record = IdempotencyKey(
        key=key,
        user_id=user_id,
        scope=scope,
        request_hash=fingerprint,
        status=STATUS_IN_PROGRESS,
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        # Otra peticion gano la carrera por la misma clave.
        await db.rollback()
        existing = await _find(db, key, user_id, scope)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La clave de idempotencia esta en uso; reintenta la operacion.",
            ) from None
        return _resolve(existing, fingerprint)
    return IdempotentStart(record=record)


def complete(
    db: AsyncSession,
    record: IdempotencyKey | None,
    *,
    status_code: int,
    body: dict,
    resource_id: UUID | None = None,
) -> None:
    """Marca la clave como completada dentro de la transaccion en curso."""
    if record is None:
        return
    record.status = STATUS_COMPLETED
    record.response_status = status_code
    record.response_body = body
    record.resource_id = resource_id


async def release(db: AsyncSession, record: IdempotencyKey | None) -> None:
    """Libera la clave cuando la operacion se rechaza y no crea nada."""
    if record is None:
        return
    await db.delete(record)
    await db.flush()
