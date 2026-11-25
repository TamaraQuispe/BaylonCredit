"""Cola persistente de revisiones humanas de credito (P1-02).

Una evaluacion que requiere revision obligatoria o una concesion bloqueada
genera un item pendiente. Reevaluar deuda al resolver; no duplicar items
para la misma evaluacion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import (
    CreditEvaluation,
    CreditReview,
    CreditReviewResolution,
    CreditReviewStatus,
)
from app.models.user import User, UserRole


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
    )
    db.add(review)
    await db.flush()
    return review


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
    review.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    return review


async def expire_review(db: AsyncSession, review: CreditReview) -> CreditReview:
    if review.status == CreditReviewStatus.RESOLVED:
        return review
    review.status = CreditReviewStatus.EXPIRED
    review.resolution = CreditReviewResolution.EXPIRED
    review.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    return review


def can_resolve(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT}


def can_assign(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT}