"""Make admin.permissions non-nullable

Revision ID: e08f30ab358c
Revises: e9b2b884612e
Create Date: 2023-05-27 23:11:10.973998

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e08f30ab358c"
down_revision = "e9b2b884612e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("admin") as batch_op:
        batch_op.alter_column(
            "permissions",
            existing_type=sa.Enum("full", name="adminpermissions"),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("admin") as batch_op:
        batch_op.alter_column(
            "permissions", sa.Enum("full", name="adminpermissions"), nullable=True
        )
