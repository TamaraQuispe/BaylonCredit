"""Add optional OpenRouter explanations to credit evaluations.

Revision ID: 20260912_0014
Revises: 20260911_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0014"
down_revision: str | None = "20260911_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("credit_evaluations", sa.Column("ai_explanation", sa.Text(), nullable=True))
    op.add_column("credit_evaluations", sa.Column("ai_risk_factors", sa.JSON(), nullable=True))
    op.add_column("credit_evaluations", sa.Column("ai_recommendations", sa.JSON(), nullable=True))
    op.add_column(
        "credit_evaluations",
        sa.Column("ai_status", sa.String(length=20), server_default="disabled", nullable=False),
    )
    op.add_column("credit_evaluations", sa.Column("ai_model", sa.String(length=120)))
    op.add_column("credit_evaluations", sa.Column("ai_prompt_version", sa.String(length=40)))
    op.add_column(
        "credit_evaluations", sa.Column("ai_generated_at", sa.DateTime(timezone=True))
    )


def downgrade() -> None:
    op.drop_column("credit_evaluations", "ai_generated_at")
    op.drop_column("credit_evaluations", "ai_prompt_version")
    op.drop_column("credit_evaluations", "ai_model")
    op.drop_column("credit_evaluations", "ai_status")
    op.drop_column("credit_evaluations", "ai_recommendations")
    op.drop_column("credit_evaluations", "ai_risk_factors")
    op.drop_column("credit_evaluations", "ai_explanation")
