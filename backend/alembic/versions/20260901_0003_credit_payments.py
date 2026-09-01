"""Add direct credits and transactional payments.

Revision ID: 20260901_0003
Revises: 20260901_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0003"
down_revision: str | None = "20260901_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    op.add_column("credits", sa.Column("created_by_id", sa.Uuid(), nullable=True))
    op.add_column("credits", sa.Column("credit_date", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE credits
        SET created_by_id = sales.created_by_id,
            credit_date = CAST(sales.created_at AS date)
        FROM sales
        WHERE credits.sale_id = sales.id
        """
    )
    op.alter_column("credits", "created_by_id", nullable=False)
    op.alter_column("credits", "credit_date", nullable=False)
    op.alter_column("credits", "sale_id", existing_type=sa.Uuid(), nullable=True)
    op.create_foreign_key(
        op.f("fk_credits_created_by_id_users"),
        "credits",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "payments",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("client_name", sa.String(length=160), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("method", sa.String(length=60), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("remaining_balance", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("registered_by_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_payments_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registered_by_id"],
            ["users.id"],
            name=op.f("fk_payments_registered_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
    )
    op.create_index(op.f("ix_payments_client_id"), "payments", ["client_id"], unique=False)
    op.create_index(op.f("ix_payments_code"), "payments", ["code"], unique=True)

    op.create_table(
        "payment_allocations",
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("credit_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["credit_id"],
            ["credits.id"],
            name=op.f("fk_payment_allocations_credit_id_credits"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name=op.f("fk_payment_allocations_payment_id_payments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_allocations")),
    )
    op.create_index(
        op.f("ix_payment_allocations_credit_id"),
        "payment_allocations",
        ["credit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_allocations_payment_id"),
        "payment_allocations",
        ["payment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_allocations_payment_id"), table_name="payment_allocations")
    op.drop_index(op.f("ix_payment_allocations_credit_id"), table_name="payment_allocations")
    op.drop_table("payment_allocations")
    op.drop_index(op.f("ix_payments_code"), table_name="payments")
    op.drop_index(op.f("ix_payments_client_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_constraint(op.f("fk_credits_created_by_id_users"), "credits", type_="foreignkey")
    op.alter_column("credits", "sale_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("credits", "credit_date")
    op.drop_column("credits", "created_by_id")
