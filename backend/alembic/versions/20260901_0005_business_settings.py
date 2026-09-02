"""Add business settings singleton.

Revision ID: 20260901_0005
Revises: 20260901_0004
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0005"
down_revision: str | None = "20260901_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_name", sa.String(length=160), nullable=False),
        sa.Column("business_phone", sa.String(length=30), nullable=False),
        sa.Column("business_address", sa.String(length=255), nullable=False),
        sa.Column("default_credit_term_days", sa.Integer(), nullable=False),
        sa.Column("max_credit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_alerts_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_business_settings_updated_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_settings")),
    )
    op.execute(
        sa.text(
            "INSERT INTO business_settings "
            "(id, business_name, business_phone, business_address, "
            " default_credit_term_days, max_credit_amount, due_alerts_enabled) "
            "VALUES "
            "('00000000-0000-0000-0000-0000000000c0', 'Cervecería Baylón', "
            " '+51 987 654 321', 'Av. Principal 123, Lima, Perú', 15, 200.00, true)"
        )
    )


def downgrade() -> None:
    op.drop_table("business_settings")