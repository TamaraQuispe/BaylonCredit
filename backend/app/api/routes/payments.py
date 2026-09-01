from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.client import Client
from app.models.commerce import Credit, CreditStatus, Payment, PaymentAllocation
from app.models.user import User, UserRole
from app.schemas.finance import PaymentCreate, PaymentRead

router = APIRouter(prefix="/payments", tags=["payments"])
can_write = require_roles(UserRole.ADMIN, UserRole.OPERATOR)


async def serialize_payment(db: AsyncSession, payment: Payment) -> PaymentRead:
    rows = (
        await db.execute(
            select(PaymentAllocation, Credit)
            .join(Credit, Credit.id == PaymentAllocation.credit_id)
            .where(PaymentAllocation.payment_id == payment.id)
        )
    ).all()
    registered_by = await db.get(User, payment.registered_by_id)
    return PaymentRead(
        id=payment.id,
        code=payment.code,
        client_id=payment.client_id,
        client_name=payment.client_name,
        amount=payment.amount,
        credit_ids=[allocation.credit_id for allocation, _ in rows],
        credit_codes=[credit.code for _, credit in rows],
        credit_dates=[credit.credit_date for _, credit in rows],
        payment_date=payment.payment_date,
        method=payment.method,
        reference=payment.reference,
        remaining_balance=payment.remaining_balance,
        registered_by=registered_by.full_name if registered_by else "Usuario no disponible",
        created_at=payment.created_at,
    )


@router.get("", response_model=list[PaymentRead])
async def list_payments(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentRead]:
    payments = list(
        await db.scalars(
            select(Payment).order_by(Payment.created_at.desc()).offset(offset).limit(limit)
        )
    )
    return [await serialize_payment(db, payment) for payment in payments]


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> PaymentRead:
    client = await db.get(Client, payload.client_id)
    if not client or not client.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    allocation_map = {allocation.credit_id: allocation.amount for allocation in payload.allocations}
    credits = list(
        await db.scalars(
            select(Credit)
            .where(Credit.id.in_(allocation_map))
            .order_by(Credit.id)
            .with_for_update()
        )
    )
    if len(credits) != len(allocation_map):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="One or more credits do not exist"
        )

    amount = Decimal("0")
    for credit in credits:
        applied = allocation_map[credit.id]
        if credit.client_id != payload.client_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Credit belongs to another client"
            )
        if applied > credit.pending_amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment exceeds balance for {credit.code}",
            )
        credit.pending_amount -= applied
        credit.status = CreditStatus.PAID if credit.pending_amount == 0 else CreditStatus.CURRENT
        amount += applied

    await db.flush()
    remaining_balance = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
                Credit.client_id == payload.client_id
            )
        )
        or 0
    )
    client_name = client.business_name or f"{client.first_name} {client.last_name}"
    payment = Payment(
        code=f"P-{date.today().year}-{uuid4().hex[:8].upper()}",
        client_id=client.id,
        client_name=client_name,
        amount=amount,
        payment_date=payload.payment_date,
        method=payload.method,
        reference=payload.reference,
        remaining_balance=remaining_balance,
        registered_by_id=current_user.id,
    )
    db.add(payment)
    await db.flush()
    db.add_all(
        [
            PaymentAllocation(
                payment_id=payment.id, credit_id=credit.id, amount=allocation_map[credit.id]
            )
            for credit in credits
        ]
    )
    await db.commit()
    await db.refresh(payment)
    return await serialize_payment(db, payment)
