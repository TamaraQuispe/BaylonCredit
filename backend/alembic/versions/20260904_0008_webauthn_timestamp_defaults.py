"""Add timestamp defaults to WebAuthn credentials.

Revision ID: 20260904_0008
Revises: 20260903_0007
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260904_0008"
down_revision: str | None = "20260903_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "webauthn_credentials",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.alter_column(
        "webauthn_credentials",
        "updated_at",
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def downgrade() -> None:
    op.alter_column("webauthn_credentials", "updated_at", server_default=None)
    op.alter_column("webauthn_credentials", "created_at", server_default=None)
