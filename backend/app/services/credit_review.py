"""Cola persistente de revisiones humanas de credito (P1-02).

Una evaluacion que requiere revision obligatoria o una concesion bloqueada
genera un item pendiente. Reevaluar deuda al resolver; no duplicar items
para la misma evaluacion.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.commerce import (
    CreditEvaluation,
    CreditReview,
    CreditReviewResolution,
    CreditReviewStatus,
)
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# Filas maximas que se cierran por transaccion. Evita que un backlog grande
# bloquee la cola o supere el command_timeout de la base de datos.
REVIEW_EXPIRY_BATCH_SIZE = 200


def _review_ttl() -> timedelta:
    return timedelta(hours=get_settings().credit_review_ttl_hours)


async def get_review_by_evaluation(
    db: AsyncSession, evaluation_id: UUID
) -> CreditReview | None:
    return await db.scalar(
        select(CreditReview).where(CreditReview.evaluation_id == evaluation_id)
    )


async def enqueue_review(
    db: AsyncSession,
    *,
    evaluation: CreditEvaluation,
    decision: str,
    reason: str | None = None,
    priority: int = 0,
    model_version: str | None = None,
    policy_version: str | None = None,
    feature_schema_version: str | None = None,
    threshold: float | None = None,
) -> CreditReview:
    """Crea un item pendiente si no existe uno para la evaluacion."""
    existing = await get_review_by_evaluation(db, evaluation.id)
    if existing is not None:
        return existing
    review = CreditReview(
        evaluation_id=evaluation.id,
        client_id=evaluation.client_id,
        requested_amount=evaluation.requested_amount,
        score=evaluation.score,
        risk=evaluation.risk,
        decision=decision,
        reason=reason,
        priority=priority,
        status=CreditReviewStatus.PENDING,
        model_version=model_version or evaluation.model_version,
        policy_version=policy_version,
        feature_schema_version=feature_schema_version,
        threshold=threshold,
        expires_at=datetime.now(UTC) + _review_ttl(),
    )
    db.add(review)
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        existing = await get_review_by_evaluation(db, evaluation.id)
        if existing is not None:
            return existing
        raise
    return review


async def expire_overdue_reviews(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    batch_size: int = REVIEW_EXPIRY_BATCH_SIZE,
    review_id: UUID | None = None,
) -> int:
    """Marca como expiradas las revisiones pendientes o asignadas vencidas.

    Usa ``expires_at``; los items creados antes de existir ese plazo aplican
    el TTL desde ``created_at``. Procesa como maximo ``batch_size`` filas por
    llamada (o solo ``review_id`` si se indica) y devuelve cuantas revisiones
    se expiraron.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")
    moment = now or datetime.now(UTC)
    stale_created_before = moment - _review_ttl()
    conditions = [
        CreditReview.status.in_(
            [CreditReviewStatus.PENDING, CreditReviewStatus.ASSIGNED]
        ),
        or_(
            CreditReview.expires_at <= moment,
            and_(
                CreditReview.expires_at.is_(None),
                CreditReview.created_at <= stale_created_before,
            ),
        ),
    ]
    if review_id is not None:
        conditions.append(CreditReview.id == review_id)
    overdue = list(
        await db.scalars(
            select(CreditReview)
            .where(*conditions)
            # Evita pisar una revision que otra peticion esta resolviendo.
            .with_for_update(skip_locked=True)
            .order_by(CreditReview.created_at)
            .limit(1 if review_id is not None else batch_size)
        )
    )
    for review in overdue:
        await expire_review(db, review, flush=False)
    if overdue:
        await db.flush()
    return len(overdue)


async def expire_reviews_once(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    *,
    batch_size: int = REVIEW_EXPIRY_BATCH_SIZE,
) -> int:
    """Ejecuta un ciclo de expiracion completo, en lotes y con su propia sesion."""
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")
    factory = session_factory or SessionFactory
    total = 0
    while True:
        async with factory() as db:
            expired = await expire_overdue_reviews(db, batch_size=batch_size)
            await db.commit()
        total += expired
        if expired < batch_size:
            break
    if total:
        logger.info("Revisiones de credito expiradas: %s", total)
    return total


async def review_expiry_loop(interval_minutes: int) -> None:
    """Cierra revisiones vencidas periodicamente mientras viva la API."""
    while True:
        try:
            await expire_reviews_once()
        except Exception:  # noqa: BLE001
            logger.exception("Fallo el ciclo de expiracion de revisiones")
        await asyncio.sleep(interval_minutes * 60)


async def assign_review(
    db: AsyncSession, review: CreditReview, user: User
) -> CreditReview:
    if review.status not in {CreditReviewStatus.PENDING, CreditReviewStatus.ASSIGNED}:
        raise ValueError("La revision ya fue resuelta o expiro.")
    review.status = CreditReviewStatus.ASSIGNED
    review.assigned_to_id = user.id
    await db.flush()
    return review


async def resolve_review(
    db: AsyncSession,
    review: CreditReview,
    *,
    user: User,
    resolution: CreditReviewResolution,
    note: str | None = None,
) -> CreditReview:
    if review.status == CreditReviewStatus.RESOLVED:
        raise ValueError("La revision ya fue resuelta.")
    if review.status == CreditReviewStatus.EXPIRED:
        raise ValueError("La revision expiro.")
    review.status = CreditReviewStatus.RESOLVED
    review.resolution = resolution
    review.resolution_note = (note or "").strip() or None
    review.resolved_by_id = user.id
    review.resolved_at = datetime.now(UTC)
    await db.flush()
    return review


async def expire_review(
    db: AsyncSession, review: CreditReview, *, flush: bool = True
) -> CreditReview:
    if review.status == CreditReviewStatus.RESOLVED:
        return review
    review.status = CreditReviewStatus.EXPIRED
    review.resolution = CreditReviewResolution.EXPIRED
    review.resolved_at = datetime.now(UTC)
    if flush:
        await db.flush()
    return review


def can_resolve(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT}


def can_assign(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT}