"""Persist managed profile photo references without rewriting legacy URLs."""

import sqlalchemy as sa

from alembic import op

revision = "0015_profile_photo"
down_revision = "0014_keyboard_shortcuts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_photo", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Managed URLs have no meaning without the reference; legacy URLs are retained.
    op.execute(
        "UPDATE users SET profile_image_url = NULL WHERE profile_image_url LIKE '/api/v1/auth/me/photo?version=%'"
    )
    op.drop_column("users", "profile_photo")
