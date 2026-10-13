"""Persistent user notification inbox."""

import sqlalchemy as sa

from alembic import op

revision = "0017_notification_inbox"
down_revision = "0016_personal_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inbox_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_path", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_inbox_owner_id", "inbox_notifications", ["user_id", "id"])


def downgrade() -> None:
    op.drop_table("inbox_notifications")
