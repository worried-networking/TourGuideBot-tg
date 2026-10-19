"""Add terms & support message settings

Revision ID: 972be5c0855a
Revises: b44bd4455523
Create Date: 2023-05-18 18:46:41.449325

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "972be5c0855a"
down_revision = "b44bd4455523"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch_op:
        bind = batch_op.get_bind()
        if bind.engine.name == "postgresql":
            batch_op.execute("ALTER TYPE settingskey ADD VALUE 'support_message'")
            batch_op.execute("ALTER TYPE settingskey ADD VALUE 'terms_message'")
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
                    name="settingskey",
                ),
                existing_type=sa.Enum(
                    "guide_welcome_message",
                    "audio_to_voice",
                    "delay_between_messages",
                    name="settingskey",
                ),
            )


def downgrade() -> None:
    with op.batch_alter_table("settings") as batch_op:
        bind = batch_op.get_bind()
        if bind.engine.name == "postgresql":
            raise RuntimeError("Postgres downgrade not supported here")
        else:
            batch_op.alter_column(
                "key",
                nullable=False,
                existing_nullable=False,
                type_=sa.Enum(
                    "guide_welcome_message",
                    "audio_to_voice",
                    "delay_between_messages",
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
