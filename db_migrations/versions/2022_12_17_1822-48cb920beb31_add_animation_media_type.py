"""Add animation media type

Revision ID: 48cb920beb31
Revises: dd186ed90dec
Create Date: 2022-12-17 18:22:10.699454

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "48cb920beb31"
down_revision = "dd186ed90dec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tour_section_content") as batch_op:
        batch_op.alter_column(
            "message_type",
            nullable=False,
            existing_nullable=False,
            type_=sa.Enum(
                "text",
                "location",
                "audio",
                "voice",
                "video",
                "video_note",
                "photo",
                "media_group",
                "animation",
                name="messagetype",
            ),
            existing_type=sa.Enum(
                "text",
                "location",
                "audio",
                "voice",
                "video",
                "video_note",
                "photo",
                "media_group",
                name="messagetype",
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("tour_section_content") as batch_op:
        batch_op.alter_column(
            "message_type",
            nullable=False,
            existing_nullable=False,
            type_=sa.Enum(
                "text",
                "location",
                "audio",
                "voice",
                "video",
                "video_note",
                "photo",
                "media_group",
                name="messagetype",
            ),
            existing_type=sa.Enum(
                "text",
                "location",
                "audio",
                "voice",
                "video",
                "video_note",
                "photo",
                "media_group",
                "animation",
                name="messagetype",
            ),
        )
