"""expand auth identities for multi-provider support

Revision ID: 0002_auth_identities_multi
Revises: 0001_initial_auth_schema
Create Date: 2026-03-21 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_auth_identities_multi"
down_revision = "0001_initial_auth_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(length=64), nullable=True),
        sa.Column("last_login_user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "identifier",
            name="uq_auth_identities_provider_identifier",
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            name="uq_auth_identities_user_provider",
        ),
    )
    op.create_index(
        "ix_auth_identities_identifier",
        "auth_identities",
        ["identifier"],
        unique=False,
    )

    op.execute(
        sa.text("""
            INSERT INTO auth_identities (
                user_id,
                provider,
                identifier,
                last_login_at,
                last_login_ip,
                last_login_user_agent
            )
            SELECT
                user_id,
                provider,
                identifier,
                last_login_at,
                last_login_ip,
                last_login_user_agent
            FROM auth_records
            """)
    )

    op.drop_index("ix_auth_records_identifier", table_name="auth_records")
    op.drop_table("auth_records")


def downgrade() -> None:
    op.create_table(
        "auth_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(length=64), nullable=True),
        sa.Column("last_login_user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_auth_records_identifier", "auth_records", ["identifier"], unique=False)

    op.execute(
        sa.text("""
            INSERT INTO auth_records (
                user_id,
                provider,
                identifier,
                last_login_at,
                last_login_ip,
                last_login_user_agent
            )
            SELECT
                chosen.user_id,
                chosen.provider,
                chosen.identifier,
                chosen.last_login_at,
                chosen.last_login_ip,
                chosen.last_login_user_agent
            FROM auth_identities AS chosen
            JOIN (
                SELECT
                    user_id,
                    COALESCE(
                        MAX(CASE WHEN provider = 'email' THEN id END),
                        MIN(id)
                    ) AS selected_id
                FROM auth_identities
                GROUP BY user_id
            ) AS selected
                ON selected.selected_id = chosen.id
            """)
    )

    op.drop_index("ix_auth_identities_identifier", table_name="auth_identities")
    op.drop_table("auth_identities")
