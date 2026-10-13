"""add usage count and expiry to api keys

Revision ID: 0006_api_keys_usage_and_expiry
Revises: 0005_users_role_rbac
Create Date: 2026-05-02 00:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_api_keys_usage_and_expiry"
down_revision = "0005_users_role_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("request_count", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column("api_keys", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "expires_at")
    op.drop_column("api_keys", "request_count")
