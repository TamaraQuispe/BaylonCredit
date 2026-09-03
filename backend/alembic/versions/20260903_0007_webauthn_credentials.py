"""Add webauthn_credentials table.

Revision ID: 20260903_0007
Revises: 20260902_0006
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0007"
down_revision: str | None = "20260902_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("credential_id", sa.String(length=255), nullable=False),
        sa.Column("credential_public_key", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("device_type", sa.String(length=40), nullable=False),
        sa.Column("backed_up", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("transports", sa.Text(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_webauthn_credentials_user_id"),
        "webauthn_credentials",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_webauthn_credentials_credential_id"),
        "webauthn_credentials",
        ["credential_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_webauthn_credentials_credential_id"), table_name="webauthn_credentials")
    op.drop_index(op.f("ix_webauthn_credentials_user_id"), table_name="webauthn_credentials")
    op.drop_table("webauthn_credentials")