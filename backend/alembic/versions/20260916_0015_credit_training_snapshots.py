"""Capture immutable features and outcomes for real credit-model training.

Revision ID: 20260916_0015
Revises: 20260912_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260916_0015"
down_revision: str | None = "20260912_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("credit_evaluations", sa.Column("feature_snapshot", sa.JSON(), nullable=True))
    op.add_column("credits", sa.Column("evaluation_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        op.f("uq_credits_evaluation_id"), "credits", ["evaluation_id"]
    )
    op.create_foreign_key(
        op.f("fk_credits_evaluation_id_credit_evaluations"),
        "credits",
        "credit_evaluations",
        ["evaluation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_credits_evaluation_id_credit_evaluations"), "credits")
    op.drop_constraint(op.f("uq_credits_evaluation_id"), "credits")
    op.drop_column("credits", "evaluation_id")
    op.drop_column("credit_evaluations", "feature_snapshot")
