"""Store the provider subscription identity alongside its snapshot.

Revision ID: 0013_subscription_identity
Revises: 0012_subscription_snapshots
"""

import sqlalchemy as sa

from alembic import op

revision = "0013_subscription_identity"
down_revision = "0012_subscription_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "billing_customers", sa.Column("stripe_subscription_id", sa.String(255), nullable=True)
    )


def downgrade():
    op.drop_column("billing_customers", "stripe_subscription_id")
