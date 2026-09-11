"""Add WhatsApp notification tracking.

Revision ID: 20260910_0012
Revises: 20260905_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0012"
down_revision: str | None = "20260905_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_notifications",
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("template_name", sa.String(length=60), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=True),
        sa.Column("credit_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "SENT",
                "DELIVERED",
                "READ",
                "FAILED",
                name="whatsapp_notification_status",
                native_enum=False,
            ),
            server_default="sent",
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["credit_id"],
            ["credits.id"],
            name=op.f("fk_whatsapp_notifications_credit_id_credits"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["credit_evaluations.id"],
            name=op.f("fk_whatsapp_notifications_evaluation_id_credit_evaluations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_whatsapp_notifications")),
    )
    op.create_index(
        op.f("ix_whatsapp_notifications_created_at"),
        "whatsapp_notifications",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_whatsapp_notifications_credit_id"),
        "whatsapp_notifications",
        ["credit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_whatsapp_notifications_evaluation_id"),
        "whatsapp_notifications",
        ["evaluation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_whatsapp_notifications_message_id"),
        "whatsapp_notifications",
        ["message_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_whatsapp_notifications_message_id"), table_name="whatsapp_notifications")
    op.drop_index(
        op.f("ix_whatsapp_notifications_evaluation_id"), table_name="whatsapp_notifications"
    )
    op.drop_index(op.f("ix_whatsapp_notifications_credit_id"), table_name="whatsapp_notifications")
    op.drop_index(op.f("ix_whatsapp_notifications_created_at"), table_name="whatsapp_notifications")
    op.drop_table("whatsapp_notifications")