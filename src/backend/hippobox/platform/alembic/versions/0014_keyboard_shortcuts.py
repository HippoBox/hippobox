"""Persist account keyboard shortcuts.

Revision ID: 0014_keyboard_shortcuts
Revises: 0013_subscription_identity
"""

import sqlalchemy as sa

from alembic import op

revision = "0014_keyboard_shortcuts"
down_revision = "0013_subscription_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("keyboard_shortcuts", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "keyboard_shortcuts")
