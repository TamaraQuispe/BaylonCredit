from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.api.routes.settings import get_settings_record
from app.db.session import get_db
from app.models.client import Client
from app.models.commerce import (
    Credit,
    CreditStatus,
    InventoryMovement,
    InventoryMovementType,
    PaymentMode,
    Product,
    RiskLevel,
    Sale,
    SaleItem,
)
from app.models.user import User, UserRole
from app.schemas.commerce import CreditRead, SaleCreate, SaleItemRead, SaleRead
from app.services.credit_scoring import evaluate_credit

router = APIRouter(prefix="/sales", tags=["sales"])
can_sell = require_roles(UserRole.ADMIN, UserRole.OPERATOR)
CENT = Decimal("0.01")
TAX_RATE = Decimal("0.18")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


async def serialize_sale(db: AsyncSession, sale: Sale, credit: Credit | None = None) -> SaleRead:
    items = list(await db.scalars(select(SaleItem).where(SaleItem.sale_id == sale.id)))
    if credit is None:
        credit = await db.scalar(select(Credit).where(Credit.sale_id == sale.id))
    return SaleRead(
        id=sale.id,
        code=sale.code,
        payment_mode=sale.payment_mode,
        client_id=sale.client_id,
        client_name=sale.client_name,
        subtotal=sale.subtotal,
        tax=sale.tax,
        total=sale.total,
        created_at=sale.created_at,
        items=[SaleItemRead.model_validate(item, from_attributes=True) for item in items],
        credit=CreditRead.model_validate(credit, from_attributes=True) if credit else None,
    )


@router.get("", response_model=list[SaleRead])
async def list_sales(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SaleRead]:
    sales = list(
        await db.scalars(select(Sale).order_by(Sale.created_at.desc()).offset(offset).limit(limit))
    )
    return [await serialize_sale(db, sale) for sale in sales]


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
async def create_sale(
    payload: SaleCreate,
    current_user: User = Depends(can_sell),
    db: AsyncSession = Depends(get_db),
) -> SaleRead:
    product_ids = [item.product_id for item in payload.items]
    products = list(
        await db.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        )
    )
    product_map = {product.id: product for product in products}
    if len(product_map) != len(product_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="One or more products do not exist"
        )

    subtotal = Decimal("0")
    for item in payload.items:
        product = product_map[item.product_id]
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"{product.name} is inactive"
            )
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for {product.name}",
            )
        subtotal += product.price * item.quantity
    subtotal = money(subtotal)
    tax = money(subtotal * TAX_RATE)
    total = subtotal + tax

    client: Client | None = None
    credit_evaluation: tuple[int, RiskLevel, Decimal, bool, list] | None = None
    if payload.payment_mode == PaymentMode.CREDIT:
        client = await db.get(Client, payload.client_id)
        if not client or not client.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        if payload.due_date is None:
            settings = await get_settings_record(db)
            due_date = date.today() + timedelta(days=settings.default_credit_term_days)
        else:
            due_date = payload.due_date
        if due_date <= date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Due date must be after today",
            )
        credit_evaluation = await evaluate_credit(db, client.id, total)
        if not credit_evaluation[3]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Credit rejected. Recommended limit: {credit_evaluation[2]}",
            )

    client_name = (
        client.business_name or f"{client.first_name} {client.last_name}" if client else None
    )
    sale = Sale(
        code=f"V-{date.today().year}-{uuid4().hex[:8].upper()}",
        payment_mode=payload.payment_mode,
        client_id=client.id if client else None,
        client_name=client_name,
        created_by_id=current_user.id,
        subtotal=subtotal,
        tax=tax,
        total=total,
    )
    db.add(sale)
    await db.flush()

    for item in payload.items:
        product = product_map[item.product_id]
        line_subtotal = money(product.price * item.quantity)
        product.stock -= item.quantity
        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                product_category=product.category,
                unit_price=product.price,
                quantity=item.quantity,
                line_subtotal=line_subtotal,
            )
        )
        db.add(
            InventoryMovement(
                product_id=product.id,
                movement_type=InventoryMovementType.SALE,
                quantity_delta=-item.quantity,
                stock_after=product.stock,
                reference_id=sale.id,
                note=f"Sale {sale.code}",
                created_by_id=current_user.id,
            )
        )

    credit: Credit | None = None
    if client and credit_evaluation:
        score, risk, recommended_limit, _approved, _factors = credit_evaluation
        credit = Credit(
            code=f"F-{date.today().year}-{uuid4().hex[:8].upper()}",
            client_id=client.id,
            sale_id=sale.id,
            created_by_id=current_user.id,
            original_amount=total,
            pending_amount=total,
            credit_date=date.today(),
            due_date=due_date,
            status=CreditStatus.CURRENT,
            risk=risk,
            score=score,
            recommended_limit=recommended_limit,
        )
        db.add(credit)

    await db.commit()
    await db.refresh(sale)
    if credit:
        await db.refresh(credit)
    return await serialize_sale(db, sale, credit)
