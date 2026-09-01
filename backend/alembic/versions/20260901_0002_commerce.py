"""Create transactional commerce tables.

Revision ID: 20260901_0002
Revises: 20260831_0001
"""

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0002"
down_revision: str | None = "20260831_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PRODUCTS = [
    (
        "00000000-0000-0000-0000-000000000001",
        "P001",
        "Pilsen Callao 620ml",
        "Cervezas",
        "6.50",
        124,
        "sports_bar",
    ),
    (
        "00000000-0000-0000-0000-000000000002",
        "P002",
        "Inca Kola 1.5L",
        "Gaseosas",
        "7.00",
        45,
        "local_drink",
    ),
    (
        "00000000-0000-0000-0000-000000000003",
        "P003",
        "Cristal Lata 355ml",
        "Cervezas",
        "4.00",
        82,
        "sports_bar",
    ),
    (
        "00000000-0000-0000-0000-000000000004",
        "P004",
        "Cusqueña Dorada 630ml",
        "Cervezas",
        "8.50",
        31,
        "sports_bar",
    ),
    (
        "00000000-0000-0000-0000-000000000005",
        "P005",
        "Coca Cola 3L",
        "Gaseosas",
        "12.00",
        27,
        "local_drink",
    ),
    (
        "00000000-0000-0000-0000-000000000006",
        "P006",
        "Piscano 750ml",
        "Licores",
        "35.00",
        8,
        "liquor",
    ),
    (
        "00000000-0000-0000-0000-000000000007",
        "P007",
        "Whisky Johnnie Walker 750ml",
        "Licores",
        "120.00",
        14,
        "liquor",
    ),
    (
        "00000000-0000-0000-0000-000000000008",
        "P008",
        "Cigarrillos Lucky Strike",
        "Cigarrillos",
        "12.00",
        0,
        "smoking_rooms",
    ),
    (
        "00000000-0000-0000-0000-000000000009",
        "P009",
        "Agua San Luis 600ml",
        "Otros",
        "2.50",
        64,
        "water_drop",
    ),
    ("00000000-0000-0000-0000-000000000010", "P010", "Gatorade 1L", "Otros", "6.00", 11, "sports"),
]


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("icon", sa.String(length=60), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("minimum_stock", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=True)

    op.create_table(
        "sales",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column(
            "payment_mode",
            sa.Enum("CASH", "CREDIT", name="payment_mode", native_enum=False),
            nullable=False,
        ),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("client_name", sa.String(length=160), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tax", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_sales_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_sales_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales")),
    )
    op.create_index(op.f("ix_sales_code"), "sales", ["code"], unique=True)

    op.create_table(
        "sale_items",
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(length=180), nullable=False),
        sa.Column("product_category", sa.String(length=80), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_sale_items_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], name=op.f("fk_sale_items_sale_id_sales"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_items")),
    )
    op.create_index(op.f("ix_sale_items_sale_id"), "sale_items", ["sale_id"], unique=False)

    op.create_table(
        "credits",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("original_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("pending_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("CURRENT", "OVERDUE", "PAID", name="credit_status", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "risk",
            sa.Enum(
                "VERY_LOW",
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="risk_level",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("recommended_limit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_credits_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], name=op.f("fk_credits_sale_id_sales"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credits")),
        sa.UniqueConstraint("sale_id", name=op.f("uq_credits_sale_id")),
    )
    op.create_index(op.f("ix_credits_client_id"), "credits", ["client_id"], unique=False)
    op.create_index(op.f("ix_credits_code"), "credits", ["code"], unique=True)

    op.create_table(
        "inventory_movements",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "movement_type",
            sa.Enum(
                "ENTRY", "ADJUSTMENT", "SALE", name="inventory_movement_type", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_inventory_movements_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_inventory_movements_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_movements")),
    )
    op.create_index(
        op.f("ix_inventory_movements_product_id"),
        "inventory_movements",
        ["product_id"],
        unique=False,
    )

    products_table = sa.table(
        "products",
        sa.column("id", sa.Uuid()),
        sa.column("sku", sa.String()),
        sa.column("name", sa.String()),
        sa.column("category", sa.String()),
        sa.column("icon", sa.String()),
        sa.column("price", sa.Numeric()),
        sa.column("unit_cost", sa.Numeric()),
        sa.column("stock", sa.Integer()),
        sa.column("minimum_stock", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        products_table,
        [
            {
                "id": UUID(product_id),
                "sku": sku,
                "name": name,
                "category": category,
                "icon": icon,
                "price": Decimal(price),
                "unit_cost": (Decimal(price) * Decimal("0.70")).quantize(Decimal("0.01")),
                "stock": stock,
                "minimum_stock": 10,
                "is_active": True,
            }
            for product_id, sku, name, category, price, stock, icon in PRODUCTS
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_movements_product_id"), table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index(op.f("ix_credits_code"), table_name="credits")
    op.drop_index(op.f("ix_credits_client_id"), table_name="credits")
    op.drop_table("credits")
    op.drop_index(op.f("ix_sale_items_sale_id"), table_name="sale_items")
    op.drop_table("sale_items")
    op.drop_index(op.f("ix_sales_code"), table_name="sales")
    op.drop_table("sales")
    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_table("products")
