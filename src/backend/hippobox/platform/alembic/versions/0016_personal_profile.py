"""Add optional personal profile fields."""

import sqlalchemy as sa

from alembic import op

revision = "0016_personal_profile"
down_revision = "0015_profile_photo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bio", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("location", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "location")
    op.drop_column("users", "bio")
