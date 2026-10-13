"""add role column to users for rbac

Revision ID: 0005_users_role_rbac
Revises: 0004_api_keys_table
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_users_role_rbac"
down_revision = "0004_api_keys_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
