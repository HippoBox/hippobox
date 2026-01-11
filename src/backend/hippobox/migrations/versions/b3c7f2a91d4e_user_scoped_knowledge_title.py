"""user_scoped_knowledge_title

Revision ID: b3c7f2a91d4e
Revises: 9f3c2b1d7a6e
Create Date: 2026-01-11 16:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c7f2a91d4e"
down_revision: Union[str, Sequence[str], None] = "9f3c2b1d7a6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_inspector(conn):
    return sa.inspect(conn)


def _has_table(conn, table_name: str) -> bool:
    return _get_inspector(conn).has_table(table_name)


def _has_unique_constraint(conn, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name for constraint in _get_inspector(conn).get_unique_constraints(table_name)
    )


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    if not _has_table(conn, "knowledge"):
        return

    if _has_unique_constraint(conn, "knowledge", "knowledge_title_key"):
        op.drop_constraint("knowledge_title_key", "knowledge", type_="unique")

    if not _has_unique_constraint(conn, "knowledge", "uq_knowledge_user_title"):
        op.create_unique_constraint("uq_knowledge_user_title", "knowledge", ["user_id", "title"])


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    if not _has_table(conn, "knowledge"):
        return

    if _has_unique_constraint(conn, "knowledge", "uq_knowledge_user_title"):
        op.drop_constraint("uq_knowledge_user_title", "knowledge", type_="unique")

    if not _has_unique_constraint(conn, "knowledge", "knowledge_title_key"):
        op.create_unique_constraint("knowledge_title_key", "knowledge", ["title"])
