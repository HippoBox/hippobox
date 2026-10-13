"""Reserve one bounded subscription Checkout per customer across workers."""

import sqlalchemy as sa

from alembic import op

revision = "0009_billing_checkouts"
down_revision = "0008_billing_customers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_checkouts",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("livemode", sa.Boolean(), primary_key=True),
        sa.Column("creation_key", sa.String(36), nullable=False),
        sa.Column("price_id", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("billing_checkouts")
