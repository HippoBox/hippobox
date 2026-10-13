"""Private support inquiries and message history."""

import sqlalchemy as sa

from alembic import op

revision = "0019_support_inquiries"
down_revision = "0018_inbox_delivery_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inquiries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("subject", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_inquiry_request"),
    )
    op.create_index("ix_inquiry_owner_updated", "inquiries", ["user_id", "updated_at"])
    op.create_table(
        "inquiry_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "inquiry_id",
            sa.Integer(),
            sa.ForeignKey("inquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("author_role", sa.String(10), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("inquiry_id", "request_id", name="uq_inquiry_message_request"),
    )
    op.create_index("ix_inquiry_messages_inquiry_id", "inquiry_messages", ["inquiry_id"])


def downgrade() -> None:
    op.drop_table("inquiry_messages")
    op.drop_table("inquiries")
