"""Add must_change_password to users.

Revision ID: 20260902_0006
Revises: 20260901_0005
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0006"
down_revision: str | None = "20260901_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
