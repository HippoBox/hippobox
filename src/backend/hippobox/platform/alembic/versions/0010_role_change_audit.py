"""Record operator role changes and support reversible manager adoption.

Revision ID: 0010_role_change_audit
Revises: 0009_billing_checkouts
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_role_change_audit"
down_revision = "0009_billing_checkouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.role is already VARCHAR(20); existing role values are preserved.
    op.create_table(
        "role_change_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("previous_role", sa.String(20), nullable=False),
        sa.Column("new_role", sa.String(20), nullable=False),
        sa.Column("operator", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # Old releases cannot deserialize manager. Safely remove elevated read access.
    op.execute(sa.text("UPDATE users SET role = 'user' WHERE role = 'manager'"))
    op.drop_table("role_change_audit")
