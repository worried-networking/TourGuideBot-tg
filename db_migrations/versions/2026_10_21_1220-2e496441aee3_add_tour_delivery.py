"""Add tour_delivery

Revision ID: 2e496441aee3
Revises: 108a199c67fb
Create Date: 2026-10-21 12:20:33.610061

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2e496441aee3"
down_revision = "108a199c67fb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tour_delivery",
        sa.Column(
            "telegram_user_id", sa.BigInteger(), autoincrement=False, nullable=False
        ),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("tour_translation_id", sa.Integer(), nullable=False),
        sa.Column("section_position", sa.SmallInteger(), nullable=False),
        sa.Column("next_content_position", sa.SmallInteger(), nullable=False),
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column(
            "created_ts", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_ts", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["telegram_user_id"], ["telegram_user.id"]),
        sa.ForeignKeyConstraint(["tour_translation_id"], ["tour_translation.id"]),
        sa.PrimaryKeyConstraint("telegram_user_id"),
    )
    op.create_index(
        op.f("ix_tour_delivery_tour_translation_id"),
        "tour_delivery",
        ["tour_translation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tour_delivery_tour_translation_id"), table_name="tour_delivery"
    )
    op.drop_table("tour_delivery")
