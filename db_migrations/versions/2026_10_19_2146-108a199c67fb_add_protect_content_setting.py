"""Add protect_content setting

Revision ID: 108a199c67fb
Revises: dbf604473cee
Create Date: 2026-10-19 21:46:51.244666

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "108a199c67fb"
down_revision = "dbf604473cee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch_op:
        bind = batch_op.get_bind()
        if bind.engine.name == "postgresql":
            batch_op.execute(
                "ALTER TYPE settingskey ADD VALUE IF NOT EXISTS 'protect_content'"
            )
        else:
            batch_op.alter_column(
                "key",
                nullable=False,
                existing_nullable=False,
                type_=sa.Enum(
                    "guide_welcome_message",
                    "audio_to_voice",
                    "delay_between_messages",
                    "support_message",
                    "terms_message",
                    "protect_content",
                    name="settingskey",
                ),
                existing_type=sa.Enum(
                    "guide_welcome_message",
                    "audio_to_voice",
                    "delay_between_messages",
                    "support_message",
                    "terms_message",
                    name="settingskey",
                ),
            )


def downgrade() -> None:
    if op.get_bind().engine.name == "postgresql":
        raise RuntimeError("Postgres downgrade not supported here")

    op.execute("DELETE FROM settings WHERE key = 'protect_content'")

    with op.batch_alter_table("settings") as batch_op:
        batch_op.alter_column(
            "key",
            nullable=False,
            existing_nullable=False,
            type_=sa.Enum(
                "guide_welcome_message",
                "audio_to_voice",
                "delay_between_messages",
                "support_message",
                "terms_message",
                name="settingskey",
            ),
            existing_type=sa.Enum(
                "guide_welcome_message",
                "audio_to_voice",
                "delay_between_messages",
                "support_message",
                "terms_message",
                "protect_content",
                name="settingskey",
            ),
        )
