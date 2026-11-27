"""Add the research-only PROY experimental evaluation trace.

Revision ID: 20261127_0018
Revises: 20260918_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261127_0018"
down_revision: str | None = "20260918_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proy_experimental_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("requested_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("pending_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Numeric(6, 4), nullable=False),
        sa.Column("predicted", sa.Integer(), nullable=True),
        sa.Column("model_called", sa.Boolean(), nullable=False),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("policy_version", sa.String(length=40), nullable=False),
        sa.Column("feature_snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_proy_experimental_evaluations_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_proy_experimental_evaluations_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_proy_experimental_evaluations")),
    )
    op.create_index(
        op.f("ix_proy_experimental_evaluations_client_id"),
        "proy_experimental_evaluations",
        ["client_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_proy_experimental_evaluations_client_id"),
        table_name="proy_experimental_evaluations",
    )
    op.drop_table("proy_experimental_evaluations")
