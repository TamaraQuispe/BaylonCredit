"""Add persistent credit review queue.

Revision ID: 20260918_0017
Revises: 20260917_0016
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260918_0017"
down_revision: str | None = "20260917_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credit_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=True),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("requested_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(length=20), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(length=40), nullable=True),
        sa.Column("policy_version", sa.String(length=40), nullable=True),
        sa.Column("feature_schema_version", sa.String(length=40), nullable=True),
        sa.Column("threshold", sa.Numeric(6, 4), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            ["evaluation_id"],
            ["credit_evaluations.id"],
            name=op.f("fk_credit_reviews_evaluation_id_credit_evaluations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_credit_reviews_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_id"],
            ["users.id"],
            name=op.f("fk_credit_reviews_assigned_to_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["users.id"],
            name=op.f("fk_credit_reviews_resolved_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credit_reviews")),
        sa.UniqueConstraint(
            "evaluation_id", name="uq_credit_reviews_evaluation_id"
        ),
    )
    op.create_index(
        op.f("ix_credit_reviews_client_id"), "credit_reviews", ["client_id"], unique=False
    )
    op.create_index(
        op.f("ix_credit_reviews_status"), "credit_reviews", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_credit_reviews_status"), table_name="credit_reviews")
    op.drop_index(op.f("ix_credit_reviews_client_id"), table_name="credit_reviews")
    op.drop_table("credit_reviews")