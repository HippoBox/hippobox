"""Additive bridge from HippoBox 0.1 to the Blueprint platform.

Preserves physical user/credential/knowledge tables and all identifiers. The
upstream Alembic history must never be run against a HippoBox database.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect, text

from hippobox.core.settings import SETTINGS

USER_COLUMNS = {
    "profile_image_url": "TEXT",
    "bio": "VARCHAR(100)",
    "location": "VARCHAR(100)",
    "profile_photo": "JSON",
    "keyboard_shortcuts": "JSON",
}


def extend_legacy_schema(connection):
    inspector = inspect(connection)
    if not inspector.has_table("user"):
        return
    existing = {column["name"] for column in inspector.get_columns("user")}
    if not inspector.has_table("hippobox_schema"):
        if not SETTINGS.PLATFORM_MIGRATE_LEGACY:
            raise RuntimeError(
                "Legacy HippoBox database detected. Back up SQL and Qdrant, then set PLATFORM_MIGRATE_LEGACY=true for the first upgrade."
            )
        if connection.dialect.name == "sqlite":
            database = connection.engine.url.database
            if database and database != ":memory:":
                source = Path(database)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                backup = source.with_name(f"{source.name}.pre-platform-{stamp}.bak")
                with sqlite3.connect(str(source)) as old, sqlite3.connect(str(backup)) as target:
                    old.backup(target)
        elif connection.dialect.name == "postgresql":
            connection.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'MANAGER'"))
    for name, sql_type in USER_COLUMNS.items():
        if name not in existing:
            connection.execute(text(f'ALTER TABLE "user" ADD COLUMN {name} {sql_type}'))


def import_legacy_identities(connection):
    if connection.dialect.name == "sqlite":
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS hippobox_user_sequence (id INTEGER PRIMARY KEY CHECK(id=1), value INTEGER NOT NULL)"
            )
        )
        connection.execute(
            text('INSERT OR IGNORE INTO hippobox_user_sequence SELECT 1, COALESCE(MAX(id), 0) FROM "user"')
        )
    connection.execute(text("CREATE TABLE IF NOT EXISTS hippobox_schema (version INTEGER PRIMARY KEY)"))
    if connection.execute(text("SELECT version FROM hippobox_schema WHERE version = 1")).first():
        return
    inspector = inspect(connection)
    if inspector.has_table("auth"):
        connection.execute(
            text("""
            INSERT INTO auth_identities
                (user_id, provider, identifier, last_login_at, last_login_ip,
                 last_login_user_agent, created_at, updated_at)
            SELECT a.user_id, a.provider, a.identifier, a.last_login_at, a.last_login_ip,
                   a.last_login_user_agent, a.created_at, a.updated_at
            FROM auth a JOIN "user" u ON u.id = a.user_id
            WHERE NOT EXISTS (
                SELECT 1 FROM auth_identities n
                WHERE n.user_id = a.user_id AND n.provider = a.provider
            )
        """)
        )
    connection.execute(text("INSERT INTO hippobox_schema (version) VALUES (1)"))
