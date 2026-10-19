"""TelegramUser.id to BigInt

Revision ID: f0d460bb5317
Revises: 57297f62237a
Create Date: 2023-06-04 21:03:59.454407

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f0d460bb5317"
down_revision = "57297f62237a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("telegram_user") as batch_op:
        batch_op.alter_column(
            "id",
            nullable=False,
            existing_nullable=False,
            type_=sa.BigInteger(),
            existing_type=sa.Integer(),
        )


def downgrade() -> None:
    with op.batch_alter_table("telegram_user") as batch_op:
        batch_op.alter_column(
            "id",
            nullable=False,
            existing_nullable=False,
            type_=sa.Integer(),
            existing_type=sa.BigInteger(),
        )
