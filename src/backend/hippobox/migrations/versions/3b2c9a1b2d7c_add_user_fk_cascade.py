"""add_user_fk_cascade

Revision ID: 3b2c9a1b2d7c
Revises: 18071a646038
Create Date: 2026-01-03 18:20:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b2c9a1b2d7c"
down_revision: Union[str, Sequence[str], None] = "18071a646038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("auth") as batch_op:
        batch_op.create_foreign_key(
            "fk_auth_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("credential") as batch_op:
        batch_op.create_foreign_key(
            "fk_credential_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("api_key") as batch_op:
        batch_op.create_foreign_key(
            "fk_api_key_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("knowledge") as batch_op:
        batch_op.create_foreign_key(
            "fk_knowledge_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("knowledge") as batch_op:
        batch_op.drop_constraint("fk_knowledge_user_id_user", type_="foreignkey")

    with op.batch_alter_table("api_key") as batch_op:
        batch_op.drop_constraint("fk_api_key_user_id_user", type_="foreignkey")

    with op.batch_alter_table("credential") as batch_op:
        batch_op.drop_constraint("fk_credential_user_id_user", type_="foreignkey")

    with op.batch_alter_table("auth") as batch_op:
        batch_op.drop_constraint("fk_auth_user_id_user", type_="foreignkey")
