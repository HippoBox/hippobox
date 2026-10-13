"""Add Stripe customer identities, isolated between test and live mode."""

import sqlalchemy as sa

from alembic import op

revision = "0008_billing_customers"
down_revision = "0007_users_no_id_reuse"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_customers",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("livemode", sa.Boolean(), primary_key=True),
        sa.Column("creation_key", sa.String(36), nullable=False, unique=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("billing_customers")
