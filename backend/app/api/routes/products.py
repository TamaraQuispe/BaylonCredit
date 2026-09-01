from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.commerce import InventoryMovement, InventoryMovementType, Product
from app.models.user import User, UserRole
from app.schemas.commerce import ProductCreate, ProductRead, ProductUpdate, StockChange

router = APIRouter(prefix="/products", tags=["products"])
can_write = require_roles(UserRole.ADMIN, UserRole.OPERATOR)


@router.get("", response_model=list[ProductRead])
async def list_products(
    search: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=80),
    include_inactive: bool = False,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    statement = select(Product)
    if not include_inactive:
        statement = statement.where(Product.is_active.is_(True))
    if category:
        statement = statement.where(Product.category == category)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    result = await db.scalars(statement.order_by(Product.name))
    return list(result)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    current_user: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        await db.flush()
        if product.stock:
            db.add(
                InventoryMovement(
                    product_id=product.id,
                    movement_type=InventoryMovementType.ENTRY,
                    quantity_delta=product.stock,
                    stock_after=product.stock,
                    note="Initial inventory",
                    created_by_id=current_user.id,
                )
            )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="SKU already registered"
        ) from None
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    _: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.post("/{product_id}/stock", response_model=ProductRead)
async def change_stock(
    product_id: UUID,
    payload: StockChange,
    current_user: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = await db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    previous_stock = product.stock
    product.stock = (
        previous_stock + payload.quantity
        if payload.movement_type == InventoryMovementType.ENTRY
        else payload.quantity
    )
    db.add(
        InventoryMovement(
            product_id=product.id,
            movement_type=payload.movement_type,
            quantity_delta=product.stock - previous_stock,
            stock_after=product.stock,
            note=payload.note,
            created_by_id=current_user.id,
        )
    )
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_product(
    product_id: UUID,
    _: User = Depends(can_write),
    db: AsyncSession = Depends(get_db),
) -> None:
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.is_active = False
    await db.commit()
