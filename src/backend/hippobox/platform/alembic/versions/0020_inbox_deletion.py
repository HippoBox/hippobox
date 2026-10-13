"""Erase notification content while retaining delivery deduplication keys."""

import sqlalchemy as sa

from alembic import op

revision = "0020_inbox_deletion"
down_revision = "0019_support_inquiries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inbox_notifications", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("inbox_notifications", "deleted_at")
