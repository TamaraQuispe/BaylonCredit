"""Credify: organizations, roles de crédito/cobranza y política de riesgos.

Revision ID: 20260911_0013
Revises: 20260910_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0013"
down_revision: str | None = "20260910_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_ORG_ID = "00000000-0000-0000-0000-0000000000d0"
SETTINGS_ID = "00000000-0000-0000-0000-0000000000c0"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("ruc", sa.String(length=11), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.execute(
        sa.text(
            "INSERT INTO organizations "
            "(id, name, ruc, phone, address, is_active) VALUES "
            f"('{DEFAULT_ORG_ID}', 'Cervecería Baylón', NULL, '+51 987 654 321', "
            "'Av. Principal 123, Lima, Perú', true)"
        )
    )

    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_user_role")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS user_role")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT user_role "
        "CHECK (role IN ('ADMIN', 'OPERATOR', 'VIEWER', 'CREDIT', 'COLLECTIONS'))"
    )

    op.add_column(
        "users", sa.Column("organization_id", sa.Uuid(), nullable=True)
    )
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_users_organization_id_organizations"),
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "clients", sa.Column("organization_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        op.f("ix_clients_organization_id"), "clients", ["organization_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_clients_organization_id_organizations"),
        "clients",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        sa.text(
            "UPDATE users SET organization_id = cast(:org as uuid) "
            "WHERE organization_id IS NULL"
        ).bindparams(org=DEFAULT_ORG_ID)
    )

    op.add_column(
        "business_settings",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_business_settings_organization_id_organizations"),
        "business_settings",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "business_settings",
        sa.Column("scoring_low_min", sa.Integer(), server_default="80", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column("scoring_medium_min", sa.Integer(), server_default="60", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column("scoring_min_approved", sa.Integer(), server_default="60", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column("overdue_grace_days", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column("overdue_block_days", sa.Integer(), server_default="30", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column("max_exposure_percent", sa.Integer(), server_default="80", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column("new_client_blocked_days", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column("reminder_days_before", sa.Integer(), server_default="3", nullable=False),
    )
    op.add_column(
        "business_settings",
        sa.Column(
            "reminder_send_on_due_day",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "business_settings",
        sa.Column(
            "reminder_send_after_overdue",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE business_settings SET organization_id = cast(:org as uuid) "
            "WHERE id = cast(:sid as uuid)"
        ).bindparams(org=DEFAULT_ORG_ID, sid=SETTINGS_ID)
    )


def downgrade() -> None:
    op.drop_column("business_settings", "reminder_send_after_overdue")
    op.drop_column("business_settings", "reminder_send_on_due_day")
    op.drop_column("business_settings", "reminder_days_before")
    op.drop_column("business_settings", "new_client_blocked_days")
    op.drop_column("business_settings", "max_exposure_percent")
    op.drop_column("business_settings", "overdue_block_days")
    op.drop_column("business_settings", "overdue_grace_days")
    op.drop_column("business_settings", "scoring_min_approved")
    op.drop_column("business_settings", "scoring_medium_min")
    op.drop_column("business_settings", "scoring_low_min")
    op.drop_constraint(
        op.f("fk_business_settings_organization_id_organizations"),
        "business_settings",
        type_="foreignkey",
    )
    op.drop_column("business_settings", "organization_id")

    op.drop_constraint(
        op.f("fk_clients_organization_id_organizations"), "clients", type_="foreignkey"
    )
    op.drop_index(op.f("ix_clients_organization_id"), table_name="clients")
    op.drop_column("clients", "organization_id")

    op.drop_constraint(op.f("fk_users_organization_id_organizations"), "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_column("users", "organization_id")

    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS user_role")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT user_role "
        "CHECK (role IN ('ADMIN', 'OPERATOR', 'VIEWER'))"
    )

    op.drop_table("organizations")