"""Persist provider-confirmed subscription snapshots.

Revision ID: 0012_subscription_snapshots
Revises: 0011_mail_notifications
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_subscription_snapshots"
down_revision = "0011_mail_notifications"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("billing_customers", sa.Column("subscription_snapshot", sa.JSON(), nullable=True))
    op.add_column(
        "billing_customers",
        sa.Column("subscription_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("billing_customers", "subscription_synced_at")
    op.drop_column("billing_customers", "subscription_snapshot")
