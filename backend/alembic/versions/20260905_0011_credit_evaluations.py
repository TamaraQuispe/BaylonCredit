"""Add persistent credit evaluations.

Revision ID: 20260905_0011
Revises: 20260904_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_0011"
down_revision: str | None = "20260904_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credit_evaluations",
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("requested_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
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
        sa.Column("default_probability", sa.Integer(), nullable=False),
        sa.Column("recommended_limit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column(
            "model_version",
            sa.String(length=40),
            server_default="rules-v1",
            nullable=False,
        ),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "source IN ('manual', 'direct_credit', 'credit_sale')",
            name=op.f("ck_credit_evaluations_source"),
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_credit_evaluations_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_credit_evaluations_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credit_evaluations")),
    )
    op.create_index(
        op.f("ix_credit_evaluations_client_id"),
        "credit_evaluations",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_credit_evaluations_created_at"),
        "credit_evaluations",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_credit_evaluations_created_at"), table_name="credit_evaluations"
    )
    op.drop_index(
        op.f("ix_credit_evaluations_client_id"), table_name="credit_evaluations"
    )
    op.drop_table("credit_evaluations")
