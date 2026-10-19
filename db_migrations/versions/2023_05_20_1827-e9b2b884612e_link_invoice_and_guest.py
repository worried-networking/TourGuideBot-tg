"""Link invoice and guest

Revision ID: e9b2b884612e
Revises: 38c070a2b289
Create Date: 2023-05-20 18:27:58.924149

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e9b2b884612e"
down_revision = "38c070a2b289"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("invoice") as batch_op:
        batch_op.add_column(sa.Column("guest_id", sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            "fk_invoice_guest_id", "guest", ["guest_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("invoice") as batch_op:
        batch_op.drop_constraint("fk_invoice_guest_id", type_="foreignkey")
        batch_op.drop_column("guest_id")
