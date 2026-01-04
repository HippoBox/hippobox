"""normalize_topics_tags

Revision ID: 9f3c2b1d7a6e
Revises: 3b2c9a1b2d7c
Create Date: 2026-01-04 10:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9f3c2b1d7a6e"
down_revision: Union[str, Sequence[str], None] = "3b2c9a1b2d7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TOPIC_NAME = "Uncategorized"
DEFAULT_TOPIC_NORMALIZED = "uncategorized"


def _get_inspector(conn):
    return sa.inspect(conn)


def _has_table(conn, table_name: str) -> bool:
    return _get_inspector(conn).has_table(table_name)


def _has_column(conn, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in _get_inspector(conn).get_columns(table_name))


def _has_index(conn, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in _get_inspector(conn).get_indexes(table_name))


def _has_unique_constraint(conn, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in _get_inspector(conn).get_unique_constraints(table_name)
    )


def _has_fk(conn, table_name: str, fk_name: str) -> bool:
    return any(fk["name"] == fk_name for fk in _get_inspector(conn).get_foreign_keys(table_name))


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        raise RuntimeError("This migration requires PostgreSQL.")
    if not _has_table(conn, "topic"):
        op.create_table(
            "topic",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("normalized_name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("user_id", "normalized_name", name="uq_topic_user_norm"),
        )
    if _has_table(conn, "topic") and not _has_index(conn, "topic", "ix_topic_user_id"):
        op.create_index("ix_topic_user_id", "topic", ["user_id"], unique=False)
    if _has_table(conn, "topic") and not _has_index(conn, "topic", "ix_topic_normalized_name"):
        op.create_index("ix_topic_normalized_name", "topic", ["normalized_name"], unique=False)
    if _has_table(conn, "topic") and not _has_unique_constraint(conn, "topic", "uq_topic_user_norm"):
        with op.batch_alter_table("topic") as batch_op:
            batch_op.create_unique_constraint("uq_topic_user_norm", ["user_id", "normalized_name"])

    if not _has_table(conn, "tag"):
        op.create_table(
            "tag",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("normalized_name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("user_id", "normalized_name", name="uq_tag_user_norm"),
        )
    if _has_table(conn, "tag") and not _has_index(conn, "tag", "ix_tag_user_id"):
        op.create_index("ix_tag_user_id", "tag", ["user_id"], unique=False)
    if _has_table(conn, "tag") and not _has_index(conn, "tag", "ix_tag_normalized_name"):
        op.create_index("ix_tag_normalized_name", "tag", ["normalized_name"], unique=False)
    if _has_table(conn, "tag") and not _has_unique_constraint(conn, "tag", "uq_tag_user_norm"):
        with op.batch_alter_table("tag") as batch_op:
            batch_op.create_unique_constraint("uq_tag_user_norm", ["user_id", "normalized_name"])
    if _has_table(conn, "tag") and not _has_unique_constraint(conn, "tag", "uq_tag_id_user_id"):
        with op.batch_alter_table("tag") as batch_op:
            batch_op.create_unique_constraint("uq_tag_id_user_id", ["id", "user_id"])

    if _has_table(conn, "knowledge") and not _has_column(conn, "knowledge", "topic_id"):
        with op.batch_alter_table("knowledge") as batch_op:
            batch_op.add_column(sa.Column("topic_id", sa.Integer(), nullable=True))
    if _has_table(conn, "knowledge") and not _has_fk(conn, "knowledge", "fk_knowledge_topic_id_topic"):
        with op.batch_alter_table("knowledge") as batch_op:
            batch_op.create_foreign_key(
                "fk_knowledge_topic_id_topic",
                "topic",
                ["topic_id"],
                ["id"],
                ondelete="RESTRICT",
            )
    if _has_table(conn, "knowledge") and not _has_index(conn, "knowledge", "ix_knowledge_topic_id"):
        with op.batch_alter_table("knowledge") as batch_op:
            batch_op.create_index("ix_knowledge_topic_id", ["topic_id"], unique=False)
    if _has_table(conn, "knowledge") and not _has_unique_constraint(conn, "knowledge", "uq_knowledge_id_user_id"):
        with op.batch_alter_table("knowledge") as batch_op:
            batch_op.create_unique_constraint("uq_knowledge_id_user_id", ["id", "user_id"])

    if not _has_table(conn, "knowledge_tag"):
        op.create_table(
            "knowledge_tag",
            sa.Column("knowledge_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("knowledge_id", "tag_id"),
        )
    if _has_table(conn, "knowledge_tag") and not _has_index(conn, "knowledge_tag", "ix_knowledge_tag_user_id"):
        op.create_index("ix_knowledge_tag_user_id", "knowledge_tag", ["user_id"], unique=False)
    if _has_table(conn, "knowledge_tag") and not _has_index(conn, "knowledge_tag", "ix_knowledge_tag_tag_id"):
        op.create_index("ix_knowledge_tag_tag_id", "knowledge_tag", ["tag_id"], unique=False)
    if _has_table(conn, "knowledge_tag") and not _has_index(conn, "knowledge_tag", "ix_knowledge_tag_knowledge_id"):
        op.create_index("ix_knowledge_tag_knowledge_id", "knowledge_tag", ["knowledge_id"], unique=False)
    if _has_table(conn, "knowledge_tag") and not _has_fk(conn, "knowledge_tag", "fk_knowledge_tag_knowledge_user"):
        op.create_foreign_key(
            "fk_knowledge_tag_knowledge_user",
            "knowledge_tag",
            "knowledge",
            ["knowledge_id", "user_id"],
            ["id", "user_id"],
            ondelete="CASCADE",
        )
    if _has_table(conn, "knowledge_tag") and not _has_fk(conn, "knowledge_tag", "fk_knowledge_tag_tag_user"):
        op.create_foreign_key(
            "fk_knowledge_tag_tag_user",
            "knowledge_tag",
            "tag",
            ["tag_id", "user_id"],
            ["id", "user_id"],
            ondelete="CASCADE",
        )

    if _has_table(conn, "knowledge") and _has_column(conn, "knowledge", "topic"):
        conn.execute(
            sa.text(
                """
                INSERT INTO topic (user_id, name, normalized_name, created_at)
                SELECT DISTINCT
                    user_id,
                    regexp_replace(btrim(topic), '\\s+', ' ', 'g') AS name,
                    lower(regexp_replace(btrim(topic), '\\s+', ' ', 'g')) AS normalized_name,
                    now()
                FROM knowledge
                WHERE topic IS NOT NULL AND btrim(topic) <> ''
                ON CONFLICT (user_id, normalized_name) DO NOTHING
                """
            )
        )
    conn.execute(
        sa.text(
            """
            INSERT INTO topic (user_id, name, normalized_name, created_at)
            SELECT DISTINCT user_id, :default_name, :default_norm, now()
            FROM knowledge
            ON CONFLICT (user_id, normalized_name) DO NOTHING
            """
        ),
        {"default_name": DEFAULT_TOPIC_NAME, "default_norm": DEFAULT_TOPIC_NORMALIZED},
    )

    if _has_table(conn, "knowledge") and _has_column(conn, "knowledge", "topic_id"):
        conn.execute(
            sa.text(
                """
                UPDATE knowledge k
                SET topic_id = t.id
                FROM topic t
                WHERE k.topic_id IS NULL
                  AND t.user_id = k.user_id
                  AND t.normalized_name = :default_norm
                """
            ),
            {"default_norm": DEFAULT_TOPIC_NORMALIZED},
        )

    if _has_table(conn, "knowledge") and _has_column(conn, "knowledge", "topic"):
        conn.execute(
            sa.text(
                """
                UPDATE knowledge k
                SET topic_id = t.id
                FROM topic t
                WHERE t.user_id = k.user_id
                  AND t.normalized_name = CASE
                    WHEN k.topic IS NULL OR btrim(k.topic) = '' THEN :default_norm
                    ELSE lower(regexp_replace(btrim(k.topic), '\\s+', ' ', 'g'))
                  END
                """
            ),
            {"default_norm": DEFAULT_TOPIC_NORMALIZED},
        )

    if _has_table(conn, "knowledge") and _has_column(conn, "knowledge", "tags"):
        conn.execute(
            sa.text(
                """
                INSERT INTO tag (user_id, name, normalized_name, created_at)
                SELECT DISTINCT
                    k.user_id,
                    regexp_replace(regexp_replace(btrim(tag), '^#', ''), '\\s+', ' ', 'g') AS name,
                    lower(regexp_replace(regexp_replace(btrim(tag), '^#', ''), '\\s+', ' ', 'g')) AS normalized_name,
                    now()
                FROM knowledge k
                CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(k.tags::jsonb, '[]'::jsonb)) AS tag
                WHERE btrim(tag) <> ''
                ON CONFLICT (user_id, normalized_name) DO NOTHING
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO knowledge_tag (knowledge_id, tag_id, user_id, created_at)
                SELECT k.id, t.id, k.user_id, now()
                FROM knowledge k
                JOIN LATERAL jsonb_array_elements_text(COALESCE(k.tags::jsonb, '[]'::jsonb)) AS tag ON true
                JOIN tag t ON t.user_id = k.user_id
                         AND t.normalized_name = lower(
                            regexp_replace(regexp_replace(btrim(tag), '^#', ''), '\\s+', ' ', 'g')
                         )
                ON CONFLICT DO NOTHING
                """
            )
        )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_topic_owner()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.topic_id IS NULL THEN
                RAISE EXCEPTION 'topic_id cannot be null'
                    USING ERRCODE = '23502';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM topic t
                WHERE t.id = NEW.topic_id AND t.user_id = NEW.user_id
            ) THEN
                RAISE EXCEPTION 'topic_id % does not belong to user_id %',
                    NEW.topic_id, NEW.user_id
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_knowledge_topic_owner'
            ) THEN
                CREATE TRIGGER trg_knowledge_topic_owner
                BEFORE INSERT OR UPDATE OF topic_id, user_id ON knowledge
                FOR EACH ROW EXECUTE FUNCTION enforce_topic_owner();
            END IF;
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION reassign_topic_on_delete()
        RETURNS trigger AS $$
        DECLARE
            default_topic_id BIGINT;
        BEGIN
            IF OLD.normalized_name = '{DEFAULT_TOPIC_NORMALIZED}' THEN
                RAISE EXCEPTION 'cannot delete default topic';
            END IF;

            SELECT id INTO default_topic_id
            FROM topic
            WHERE user_id = OLD.user_id AND normalized_name = '{DEFAULT_TOPIC_NORMALIZED}'
            LIMIT 1;

            IF default_topic_id IS NULL THEN
                INSERT INTO topic (user_id, name, normalized_name, created_at)
                VALUES (OLD.user_id, '{DEFAULT_TOPIC_NAME}', '{DEFAULT_TOPIC_NORMALIZED}', now())
                RETURNING id INTO default_topic_id;
            END IF;

            UPDATE knowledge
            SET topic_id = default_topic_id
            WHERE user_id = OLD.user_id AND topic_id = OLD.id;

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_topic_reassign'
            ) THEN
                CREATE TRIGGER trg_topic_reassign
                BEFORE DELETE ON topic
                FOR EACH ROW EXECUTE FUNCTION reassign_topic_on_delete();
            END IF;
        END;
        $$;
        """
    )

    if _has_table(conn, "knowledge") and _has_column(conn, "knowledge", "topic_id"):
        with op.batch_alter_table("knowledge") as batch_op:
            batch_op.alter_column("topic_id", nullable=False)
    if _has_table(conn, "knowledge") and _has_column(conn, "knowledge", "topic"):
        with op.batch_alter_table("knowledge") as batch_op:
            batch_op.drop_column("topic")
    if _has_table(conn, "knowledge") and _has_column(conn, "knowledge", "tags"):
        with op.batch_alter_table("knowledge") as batch_op:
            batch_op.drop_column("tags")


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        raise RuntimeError("This migration requires PostgreSQL.")

    with op.batch_alter_table("knowledge") as batch_op:
        batch_op.add_column(sa.Column("topic", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True))

    conn.execute(
        sa.text(
            """
            UPDATE knowledge k
            SET topic = t.name
            FROM topic t
            WHERE t.id = k.topic_id
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE knowledge k
            SET tags = COALESCE(tag_list.tags, '[]'::jsonb)
            FROM (
                SELECT kt.knowledge_id AS knowledge_id,
                       jsonb_agg(t.name ORDER BY t.name) AS tags
                FROM knowledge_tag kt
                JOIN tag t ON t.id = kt.tag_id
                GROUP BY kt.knowledge_id
            ) AS tag_list
            WHERE tag_list.knowledge_id = k.id
            """
        )
    )

    op.execute("DROP TRIGGER IF EXISTS trg_topic_reassign ON topic;")
    op.execute("DROP FUNCTION IF EXISTS reassign_topic_on_delete;")
    op.execute("DROP TRIGGER IF EXISTS trg_knowledge_topic_owner ON knowledge;")
    op.execute("DROP FUNCTION IF EXISTS enforce_topic_owner;")

    op.drop_constraint("fk_knowledge_tag_tag_user", "knowledge_tag", type_="foreignkey")
    op.drop_constraint("fk_knowledge_tag_knowledge_user", "knowledge_tag", type_="foreignkey")
    op.drop_index("ix_knowledge_tag_knowledge_id", table_name="knowledge_tag")
    op.drop_index("ix_knowledge_tag_tag_id", table_name="knowledge_tag")
    op.drop_index("ix_knowledge_tag_user_id", table_name="knowledge_tag")
    op.drop_table("knowledge_tag")

    with op.batch_alter_table("knowledge") as batch_op:
        batch_op.drop_constraint("fk_knowledge_topic_id_topic", type_="foreignkey")
        batch_op.drop_index("ix_knowledge_topic_id")
        batch_op.drop_constraint("uq_knowledge_id_user_id", type_="unique")
        batch_op.drop_column("topic_id")

    with op.batch_alter_table("tag") as batch_op:
        batch_op.drop_constraint("uq_tag_id_user_id", type_="unique")

    op.drop_index("ix_tag_normalized_name", table_name="tag")
    op.drop_index("ix_tag_user_id", table_name="tag")
    op.drop_table("tag")

    op.drop_index("ix_topic_normalized_name", table_name="topic")
    op.drop_index("ix_topic_user_id", table_name="topic")
    op.drop_table("topic")
