"""Prevent deleted user IDs being reused by SQLite."""

from alembic import op

revision = "0007_users_no_id_reuse"
down_revision = "0006_api_keys_usage_and_expiry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(
            "users", recreate="always", table_kwargs={"sqlite_autoincrement": True}
        ):
            pass


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(
            "users", recreate="always", table_kwargs={"sqlite_autoincrement": False}
        ):
            pass
