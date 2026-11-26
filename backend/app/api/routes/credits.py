from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.api.routes.settings import get_settings_record
from app.db.session import get_db
from app.models.client import Client
from app.models.commerce import (
    Credit,
    CreditEvaluation,
    CreditReview,
    CreditReviewResolution,
    CreditStatus,
    Payment,
    PaymentAllocation,
    RiskLevel,
)
from app.models.user import User, UserRole
from app.schemas.finance import (
    CreditEvaluationHistoryRead,
    CreditEvaluationRead,
    CreditEvaluationRequest,
    CreditEvaluationSummary,
    CreditPaymentEntry,
    CreditReviewExpireRead,
    CreditReviewRead,
    DirectCreditCreate,
    FinanceCreditRead,
    ScoreFactorRead,
)
from app.services.ai_credit import dispatch_ai_explanation, enqueue_ai_explanation
from app.services.audit import add_audit_log
from app.services.credit_review import (
    assign_review,
    can_assign,
    can_resolve,
    enqueue_review,
    expire_overdue_reviews,
    resolve_review,
)
from app.services.credit_scoring import evaluate_and_record
from app.services.idempotency import (
    HEADER_NAME as IDEMPOTENCY_HEADER,
)
from app.services.idempotency import (
    begin as begin_idempotent_operation,
)
from app.services.idempotency import (
    complete as complete_idempotent_operation,
)
from app.services.idempotency import (
    normalize_key as normalize_idempotency_key,
)
from app.services.idempotency import (
    release as release_idempotent_operation,
)
from app.services.proy_credit_policy import (
    PENDING_BALANCE_BLOCK,
    lock_client,
    pending_balance_gate,
)
from app.services.whatsapp import enqueue_evaluation_notification

router = APIRouter(prefix="/credits", tags=["credits"])
can_write = require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT)
can_evaluate_risk = require_roles(
    UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT, UserRole.VIEWER
)
admin_only = require_roles(UserRole.ADMIN)

_RISK_ORDER = {
    RiskLevel.VERY_LOW: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


def current_status(credit: Credit) -> str:
    if credit.pending_amount == 0:
        return "pagado"
    days = (credit.due_date - date.today()).days
    if days < 0:
        return "vencido"
    if days <= 5:
        return "proximo-a-vencer"
    return "al-dia"


async def serialize_credit(db: AsyncSession, credit: Credit) -> FinanceCreditRead:
    client = await db.get(Client, credit.client_id)
    rows = (
        await db.execute(
            select(PaymentAllocation, Payment)
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(PaymentAllocation.credit_id == credit.id)
            .order_by(Payment.created_at)
        )
    ).all()
    paid_amount = credit.original_amount - credit.pending_amount
    paid_percent = float((paid_amount / credit.original_amount) * 100)
    client_name = f"{client.first_name} {client.last_name}" if client else "Cliente no disponible"
    return FinanceCreditRead(
        id=credit.id,
        code=credit.code,
        client_id=credit.client_id,
        client_name=client_name,
        client_business=client.business_name or client_name if client else client_name,
        client_phone=client.phone if client else "",
        original_amount=credit.original_amount,
        pending_amount=credit.pending_amount,
        paid_amount=paid_amount,
        paid_percent=round(paid_percent, 1),
        credit_date=credit.credit_date,
        due_date=credit.due_date,
        status=current_status(credit),
        risk=credit.risk,
        score=credit.score,
        recommended_limit=credit.recommended_limit,
        created_at=credit.created_at,
        payments=[
            CreditPaymentEntry(
                id=allocation.id,
                payment_id=payment.id,
                amount=allocation.amount,
                payment_date=payment.payment_date,
                method=payment.method,
                reference=payment.reference,
                created_at=payment.created_at,
            )
            for allocation, payment in rows
        ],
    )


def serialize_evaluation(evaluation: CreditEvaluation) -> CreditEvaluationRead:
    return CreditEvaluationRead(
        score=evaluation.score,
        risk=evaluation.risk,
        default_probability=evaluation.default_probability,
        recommended_limit=evaluation.recommended_limit,
        approved=evaluation.approved,
        requires_manual_review=any(
            factor.get("key") == "payment_history_review" for factor in evaluation.factors
        ),
        recommendation=evaluation.recommendation,
        confidence=evaluation.confidence,
        factors=[ScoreFactorRead.model_validate(factor) for factor in evaluation.factors],
        model_version=evaluation.model_version,
        calculated_at=evaluation.created_at,
        response_time_ms=evaluation.response_time_ms,
        ai_explanation=evaluation.ai_explanation,
        ai_risk_factors=evaluation.ai_risk_factors,
        ai_recommendations=evaluation.ai_recommendations,
        ai_status=evaluation.ai_status,
        ai_model=evaluation.ai_model,
        ai_prompt_version=evaluation.ai_prompt_version,
        ai_generated_at=evaluation.ai_generated_at,
    )


async def record_evaluation(
    db: AsyncSession,
    client_id: UUID,
    amount: Decimal,
    created_by_id: UUID,
    source: Literal["manual", "direct_credit", "credit_sale"],
) -> CreditEvaluation:
    client = await db.get(Client, client_id)
    if not client or not client.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    evaluation = await evaluate_and_record(
        db,
        client_id,
        amount,
        created_by_id,
        source,
    )
    await db.flush()
    return evaluation


def notify_evaluation(
    background_tasks: BackgroundTasks, evaluation_id: UUID, *, include_ai: bool = True
) -> None:
    enqueue_evaluation_notification(background_tasks, evaluation_id)
    if include_ai:
        enqueue_ai_explanation(background_tasks, evaluation_id)


@router.post("/evaluate", response_model=CreditEvaluationRead)
async def evaluate_requested_credit(
    payload: CreditEvaluationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(can_evaluate_risk),
    db: AsyncSession = Depends(get_db),
) -> CreditEvaluationRead:
    evaluation = await record_evaluation(
        db, payload.client_id, payload.amount, current_user.id, "manual"
    )
    requires_review = any(
        factor.get("key") == "payment_history_review" for factor in evaluation.factors
    )
    if requires_review:
        await enqueue_review(
            db,
            evaluation=evaluation,
            decision="REQUIRES_OWNER_REVIEW",
            reason="Sin historial pagado confirmado; revision obligatoria del propietario.",
            priority=10,
            policy_version="PROY-propuesta",
        )
    await db.commit()
    await db.refresh(evaluation)
    await dispatch_ai_explanation(evaluation.id)
    await db.refresh(evaluation)
    notify_evaluation(background_tasks, evaluation.id, include_ai=False)
    return serialize_evaluation(evaluation)


@router.get("/evaluations", response_model=list[CreditEvaluationHistoryRead])
async def list_evaluations(
    client_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(can_evaluate_risk),
    db: AsyncSession = Depends(get_db),
) -> list[CreditEvaluationHistoryRead]:
    query = (
        select(CreditEvaluation, Client)
        .join(Client, Client.id == CreditEvaluation.client_id)
        .order_by(CreditEvaluation.created_at.desc())
        .limit(limit)
    )
    if client_id is not None:
        query = query.where(CreditEvaluation.client_id == client_id)
    rows = (await db.execute(query)).all()
    return [
        CreditEvaluationHistoryRead(
            **serialize_evaluation(evaluation).model_dump(),
            id=evaluation.id,
            client_id=evaluation.client_id,
            client_name=client.business_name
            or f"{client.first_name} {client.last_name}",
            created_by_id=evaluation.created_by_id,
            requested_amount=evaluation.requested_amount,
            source=evaluation.source,
            created_at=evaluation.created_at,
            updated_at=evaluation.updated_at,
        )
        for evaluation, client in rows
    ]


@router.get("/evaluations/summary", response_model=CreditEvaluationSummary)
async def evaluation_summary(
    _: User = Depends(can_evaluate_risk),
    db: AsyncSession = Depends(get_db),
) -> CreditEvaluationSummary:
    total_clients = int(
        await db.scalar(select(func.count(Client.id)).where(Client.is_active.is_(True))) or 0
    )
    evaluated_clients = int(
        await db.scalar(
            select(func.count(distinct(CreditEvaluation.client_id)))
            .join(Client, Client.id == CreditEvaluation.client_id)
            .where(Client.is_active.is_(True))
        )
        or 0
    )
    coverage = evaluated_clients * 100 / total_clients if total_clients else 0
    return CreditEvaluationSummary(
        total_clients=total_clients,
        evaluated_clients=evaluated_clients,
        coverage_percent=round(coverage, 2),
    )


@router.get("", response_model=list[FinanceCreditRead])
async def list_credits(
    search: str | None = Query(default=None, max_length=160),
    status_filter: str | None = Query(default=None, alias="status"),
    risk: RiskLevel | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FinanceCreditRead]:
    statement = select(Credit).order_by(Credit.created_at.desc())
    if search:
        term = f"%{search.strip()}%"
        clients = select(Client.id).where(
            Client.first_name.ilike(term)
            | Client.last_name.ilike(term)
            | Client.business_name.ilike(term)
            | Client.document.ilike(term)
        )
        statement = statement.where(Credit.client_id.in_(clients))
    if risk is not None:
        statement = statement.where(Credit.risk == risk)
    credits = list(await db.scalars(statement))
    if status_filter:
        credits = [credit for credit in credits if current_status(credit) == status_filter]
    credits = credits[offset : offset + limit]
    return [await serialize_credit(db, credit) for credit in credits]




@router.get("/reviews", response_model=list[CreditReviewRead])
async def list_credit_reviews(
    status_filter: str | None = Query(default=None, alias="status"),
    client_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(can_evaluate_risk),
    db: AsyncSession = Depends(get_db),
) -> list[CreditReviewRead]:
    # Cierra las revisiones vencidas para que la cola nunca muestre items caducados.
    await expire_overdue_reviews(db)
    await db.commit()
    query = (
        select(CreditReview, Client)
        .join(Client, Client.id == CreditReview.client_id)
        .order_by(CreditReview.created_at.desc())
        .limit(limit)
    )
    if status_filter:
        query = query.where(CreditReview.status == status_filter)
    if client_id is not None:
        query = query.where(CreditReview.client_id == client_id)
    rows = (await db.execute(query)).all()
    result = []
    for review, client in rows:
        result.append(
            CreditReviewRead(
                id=review.id,
                evaluation_id=review.evaluation_id,
                client_id=review.client_id,
                client_name=client.business_name
                or f"{client.first_name} {client.last_name}",
                requested_amount=review.requested_amount,
                score=review.score,
                risk=review.risk,
                decision=review.decision,
                reason=review.reason,
                priority=review.priority,
                status=review.status,
                assigned_to_id=review.assigned_to_id,
                resolved_by_id=review.resolved_by_id,
                resolved_at=review.resolved_at,
                resolution=review.resolution,
                resolution_note=review.resolution_note,
                model_version=review.model_version,
                policy_version=review.policy_version,
                feature_schema_version=review.feature_schema_version,
                threshold=review.threshold,
                created_at=review.created_at,
                updated_at=review.updated_at,
            )
        )
    return result


@router.post("/reviews/expire", response_model=CreditReviewExpireRead)
async def expire_credit_reviews(
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> CreditReviewExpireRead:
    """Cierre manual de revisiones vencidas; el ciclo del lifespan ya lo hace solo."""
    expired = await expire_overdue_reviews(db)
    await db.commit()
    return CreditReviewExpireRead(expired=expired)


@router.post("/reviews/{review_id}/assign", response_model=CreditReviewRead)
async def assign_credit_review(
    review_id: UUID,
    current_user: User = Depends(can_evaluate_risk),
    db: AsyncSession = Depends(get_db),
) -> CreditReviewRead:
    await expire_overdue_reviews(db)
    await db.commit()
    review = await db.get(CreditReview, review_id, with_for_update=True)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision no encontrada",
        )
    if not can_assign(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permiso para asignar revisiones",
        )
    try:
        await assign_review(db, review, current_user)
    except ValueError as exc:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    await db.commit()
    await db.refresh(review)
    client = await db.get(Client, review.client_id)
    return CreditReviewRead(
        id=review.id,
        evaluation_id=review.evaluation_id,
        client_id=review.client_id,
        client_name=(
            (client.business_name or f"{client.first_name} {client.last_name}")
            if client
            else None
        ),
        requested_amount=review.requested_amount,
        score=review.score,
        risk=review.risk,
        decision=review.decision,
        reason=review.reason,
        priority=review.priority,
        status=review.status,
        assigned_to_id=review.assigned_to_id,
        resolved_by_id=review.resolved_by_id,
        resolved_at=review.resolved_at,
        resolution=review.resolution,
        resolution_note=review.resolution_note,
        model_version=review.model_version,
        policy_version=review.policy_version,
        feature_schema_version=review.feature_schema_version,
        threshold=review.threshold,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.post("/reviews/{review_id}/resolve", response_model=CreditReviewRead)
async def resolve_credit_review(
    review_id: UUID,
    resolution: str = Query(..., pattern="^(aprobada|rechazada)$"),
    note: str | None = Query(default=None, max_length=500),
    current_user: User = Depends(can_evaluate_risk),
    db: AsyncSession = Depends(get_db),
) -> CreditReviewRead:
    await expire_overdue_reviews(db)
    await db.commit()
    review = await db.get(CreditReview, review_id, with_for_update=True)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision no encontrada",
        )
    if not can_resolve(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permiso para resolver revisiones",
        )
    res = (
        CreditReviewResolution.APPROVED
        if resolution == "aprobada"
        else CreditReviewResolution.REJECTED
    )
    try:
        await resolve_review(db, review, user=current_user, resolution=res, note=note)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    await db.commit()
    await db.refresh(review)
    client = await db.get(Client, review.client_id)
    return CreditReviewRead(
        id=review.id,
        evaluation_id=review.evaluation_id,
        client_id=review.client_id,
        client_name=(
            (client.business_name or f"{client.first_name} {client.last_name}")
            if client
            else None
        ),
        requested_amount=review.requested_amount,
        score=review.score,
        risk=review.risk,
        decision=review.decision,
        reason=review.reason,
        priority=review.priority,
        status=review.status,
        assigned_to_id=review.assigned_to_id,
        resolved_by_id=review.resolved_by_id,
        resolved_at=review.resolved_at,
        resolution=review.resolution,
        resolution_note=review.resolution_note,
        model_version=review.model_version,
        policy_version=review.policy_version,
        feature_schema_version=review.feature_schema_version,
        threshold=review.threshold,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )

@router.get("/{credit_id}", response_model=FinanceCreditRead)
async def get_credit(
    credit_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinanceCreditRead:
    credit = await db.get(Credit, credit_id)
    if not credit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crédito no encontrado")
    return await serialize_credit(db, credit)


@router.post("", response_model=FinanceCreditRead, status_code=status.HTTP_201_CREATED)
async def create_credit(
    payload: DirectCreditCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(can_write),
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
    db: AsyncSession = Depends(get_db),
) -> FinanceCreditRead:
    # P0-03: con Idempotency-Key un reintento no duplica el fiado.
    start = await begin_idempotent_operation(
        db,
        key=normalize_idempotency_key(idempotency_key),
        scope="credits.create",
        user_id=current_user.id,
        payload=payload.model_dump(mode="json"),
    )
    if start.replay_body is not None:
        return JSONResponse(status_code=start.replay_status, content=start.replay_body)
    # Regla del propietario (P0-02): cualquier saldo pendiente bloquea el fiado.
    # Se lee de la base con bloqueo de cliente, antes del modelo y sin excepciones.
    client = await lock_client(db, payload.client_id)
    if client is None or not client.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    pending_gate = await pending_balance_gate(db, payload.client_id)
    if pending_gate.decision == PENDING_BALANCE_BLOCK:
        add_audit_log(
            db,
            "credit_blocked_pending_balance",
            "client",
            actor=current_user,
            entity_id=client.id,
            details={
                "pending_amount": str(pending_gate.pending_amount),
                "requested_amount": str(payload.amount),
                "manual_override_requested": payload.manual_override,
                "exception_reason": (payload.exception_reason or "").strip() or None,
            },
            description="Nuevo fiado rechazado: el cliente mantiene saldo pendiente.",
        )
        await release_idempotent_operation(db, start.record)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=pending_gate.reason
        )
    evaluation = await record_evaluation(
        db, payload.client_id, payload.amount, current_user.id, "direct_credit"
    )
    requires_review = any(
        factor.get("key") == "payment_history_review" for factor in evaluation.factors
    )
    if requires_review:
        await enqueue_review(
            db,
            evaluation=evaluation,
            decision="REQUIRES_OWNER_REVIEW",
            reason="Sin historial pagado confirmado; revision obligatoria del propietario.",
            priority=10,
            policy_version="PROY-propuesta",
        )
    approved = evaluation.approved
    overridden = False
    if not approved:
        if not payload.manual_override:
            await release_idempotent_operation(db, start.record)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=evaluation.recommendation,
            )
        requires_review = any(
            factor.get("key") == "payment_history_review" for factor in evaluation.factors
        )
        if requires_review:
            if current_user.role != UserRole.ADMIN:
                await release_idempotent_operation(db, start.record)
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Solo un administrador puede autorizar el primer fiado "
                        "sin historial de pagos."
                    ),
                )
            policy = await get_settings_record(db)
            if payload.amount > policy.max_credit_amount:
                await release_idempotent_operation(db, start.record)
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El primer fiado no puede superar el máximo configurado del negocio.",
                )
        reason = (payload.exception_reason or "").strip()
        if len(reason) < 10:
            await release_idempotent_operation(db, start.record)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar el motivo de la excepción (mínimo 10 caracteres).",
            )
        overridden = True
    if payload.due_date is None:
        settings = await get_settings_record(db)
        due_date = payload.credit_date + timedelta(days=settings.default_credit_term_days)
    else:
        due_date = payload.due_date
    credit = Credit(
        code=f"F-{date.today().year}-{uuid4().hex[:8].upper()}",
        client_id=payload.client_id,
        sale_id=None,
        evaluation_id=evaluation.id,
        created_by_id=current_user.id,
        original_amount=payload.amount,
        pending_amount=payload.amount,
        credit_date=payload.credit_date,
        due_date=due_date,
        status=CreditStatus.CURRENT,
        risk=evaluation.risk,
        score=evaluation.score,
        recommended_limit=evaluation.recommended_limit,
    )
    db.add(credit)
    await db.flush()
    if overridden:
        add_audit_log(
            db,
            "credit_overridden",
            "credit",
            actor=current_user,
            entity_id=credit.id,
            details={
                "reason": reason,
                "score": credit.score,
                "risk": credit.risk.value,
                "amount": str(credit.original_amount),
                "recommended_limit": str(credit.recommended_limit),
                "evaluation_id": str(evaluation.id),
            },
            description="Crédito aprobado como excepción fuera de la política de riesgo.",
        )
    await db.refresh(credit)
    serialized = await serialize_credit(db, credit)
    complete_idempotent_operation(
        db,
        start.record,
        status_code=status.HTTP_201_CREATED,
        body=serialized.model_dump(mode="json"),
        resource_id=credit.id,
    )
    await db.commit()
    notify_evaluation(background_tasks, evaluation.id)
    return serialized

