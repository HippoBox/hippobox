"""Deduplicate notifications without changing an already applied inbox migration."""

import sqlalchemy as sa

from alembic import op

revision = "0018_inbox_delivery_key"
down_revision = "0017_notification_inbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inbox_notifications", sa.Column("delivery_key", sa.String(64), nullable=True))
    op.create_index("ix_inbox_delivery_key", "inbox_notifications", ["delivery_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_inbox_delivery_key", table_name="inbox_notifications")
    op.drop_column("inbox_notifications", "delivery_key")
