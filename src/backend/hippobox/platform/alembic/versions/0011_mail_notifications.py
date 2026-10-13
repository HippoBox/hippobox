"""Encrypted durable lifecycle notifications.

Revision ID: 0011_mail_notifications
Revises: 0010_role_change_audit
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_mail_notifications"
down_revision = "0010_role_change_audit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mail_notifications",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("payload", sa.Text()),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease", sa.String(36)),
        sa.Column("leased_until", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sa.String(40)),
    )


def downgrade():
    op.drop_table("mail_notifications")
