"""Add image URL to products.

Revision ID: 20260904_0009
Revises: 20260904_0008
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260904_0009"
down_revision: str | None = "20260904_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_url")
