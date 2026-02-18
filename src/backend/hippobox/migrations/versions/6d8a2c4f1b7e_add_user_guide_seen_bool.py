"""add_user_guide_seen_bool

Revision ID: 6d8a2c4f1b7e
Revises: b3c7f2a91d4e
Create Date: 2026-02-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6d8a2c4f1b7e"
down_revision: Union[str, Sequence[str], None] = "b3c7f2a91d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(conn)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    if _has_column(conn, "user", "guide_seen"):
        return
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column("guide_seen", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    if not _has_column(conn, "user", "guide_seen"):
        return
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("guide_seen")
