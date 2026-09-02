from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.api.routes.settings import get_settings_record
from app.db.session import get_db
from app.models.client import Client
from app.models.commerce import Credit, CreditStatus, Payment, PaymentAllocation
from app.models.user import User, UserRole
from app.schemas.finance import (
    CreditEvaluationRead,
    CreditEvaluationRequest,
    CreditPaymentEntry,
    DirectCreditCreate,
    FinanceCreditRead,
)
from app.services.credit_scoring import evaluate_credit

router = APIRouter(prefix="/credits", tags=["credits"])
can_write = require_roles(UserRole.ADMIN, UserRole.OPERATOR)


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


async def evaluate(db: AsyncSession, client_id: UUID, amount: Decimal) -> CreditEvaluationRead:
    started_at = perf_counter()
    client = await db.get(Client, client_id)
    if not client or not client.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    score, risk, recommended_limit, approved = await evaluate_credit(db, client_id, amount)
    return CreditEvaluationRead(
        score=score,
        risk=risk,
        default_probability=max(2, 100 - score),
        recommended_limit=recommended_limit,
        approved=approved,
        recommendation=(
            f"Credit approved up to S/ {recommended_limit}."
            if approved
            else f"Amount exceeds the recommended limit of S/ {recommended_limit}."
        ),
        calculated_at=datetime.now(UTC),
        response_time_ms=round((perf_counter() - started_at) * 1000),
    )


@router.post("/evaluate", response_model=CreditEvaluationRead)
async def evaluate_requested_credit(
    payload: CreditEvaluationRequest,
    _: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> CreditEvaluationRead:
    return await evaluate(db, payload.client_id, payload.amount)


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
    evaluation = await evaluate(db, payload.client_id, payload.amount)
    if not evaluation.approved and not payload.manual_override:
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
