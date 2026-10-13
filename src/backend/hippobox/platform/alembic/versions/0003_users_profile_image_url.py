"""add profile image url to users

Revision ID: 0003_users_profile_image_url
Revises: 0002_auth_identities_multi
Create Date: 2026-04-04 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_users_profile_image_url"
down_revision = "0002_auth_identities_multi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_image_url")
