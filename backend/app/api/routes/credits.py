from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.api.routes.settings import get_settings_record
from app.db.session import get_db
from app.models.client import Client
from app.models.commerce import (
    Credit,
    CreditEvaluation,
    CreditStatus,
    Payment,
    PaymentAllocation,
)
from app.models.user import User, UserRole
from app.schemas.finance import (
    CreditEvaluationHistoryRead,
    CreditEvaluationRead,
    CreditEvaluationRequest,
    CreditEvaluationSummary,
    CreditPaymentEntry,
    DirectCreditCreate,
    FinanceCreditRead,
    ScoreFactorRead,
)
from app.services.credit_scoring import evaluate_and_record

router = APIRouter(prefix="/credits", tags=["credits"])
can_write = require_roles(UserRole.ADMIN, UserRole.OPERATOR)
can_evaluate_risk = require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)


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
        recommendation=evaluation.recommendation,
        confidence=evaluation.confidence,
        factors=[ScoreFactorRead.model_validate(factor) for factor in evaluation.factors],
        calculated_at=evaluation.created_at,
        response_time_ms=evaluation.response_time_ms,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return await evaluate_and_record(
        db,
        client_id,
        amount,
        created_by_id,
        source,
    )


@router.post("/evaluate", response_model=CreditEvaluationRead)
async def evaluate_requested_credit(
    payload: CreditEvaluationRequest,
    current_user: User = Depends(can_evaluate_risk),
    db: AsyncSession = Depends(get_db),
) -> CreditEvaluationRead:
    evaluation = await record_evaluation(
        db, payload.client_id, payload.amount, current_user.id, "manual"
    )
    await db.commit()
    await db.refresh(evaluation)
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
            model_version=evaluation.model_version,
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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FinanceCreditRead]:
    credits = list(
        await db.scalars(
            select(Credit).order_by(Credit.created_at.desc()).offset(offset).limit(limit)
        )
    )
    return [await serialize_credit(db, credit) for credit in credits]


@router.get("/{credit_id}", response_model=FinanceCreditRead)
async def get_credit(
    credit_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinanceCreditRead:
    credit = await db.get(Credit, credit_id)
    if not credit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit not found")
    return await serialize_credit(db, credit)


@router.post("", response_model=FinanceCreditRead, status_code=status.HTTP_201_CREATED)
async def create_credit(
    payload: DirectCreditCreate,
    current_user: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> FinanceCreditRead:
    evaluation = await record_evaluation(
        db, payload.client_id, payload.amount, current_user.id, "direct_credit"
    )
    if not evaluation.approved and not payload.manual_override:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=evaluation.recommendation,
        )
    if payload.due_date is None:
        settings = await get_settings_record(db)
        due_date = payload.credit_date + timedelta(days=settings.default_credit_term_days)
    else:
        due_date = payload.due_date
    credit = Credit(
        code=f"F-{date.today().year}-{uuid4().hex[:8].upper()}",
        client_id=payload.client_id,
        sale_id=None,
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
    await db.commit()
    await db.refresh(credit)
    return await serialize_credit(db, credit)
