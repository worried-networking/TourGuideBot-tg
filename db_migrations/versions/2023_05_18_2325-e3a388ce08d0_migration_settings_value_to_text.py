"""Migration settings` value to text

Revision ID: e3a388ce08d0
Revises: 972be5c0855a
Create Date: 2023-05-18 23:25:47.605413

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e3a388ce08d0"
down_revision = "972be5c0855a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch_op:
        batch_op.alter_column(
            "value",
            nullable=False,
            existing_nullable=False,
            type_=sa.Text(),
            existing_type=sa.String(),
        )


def downgrade() -> None:
    with op.batch_alter_table("settings") as batch_op:
        batch_op.alter_column(
            "value",
            nullable=False,
            existing_nullable=False,
            type_=sa.String(),
            existing_type=sa.Text(),
        )
