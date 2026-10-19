"""Multiple guests purchase

Revision ID: dbf604473cee
Revises: f0d460bb5317
Create Date: 2023-07-22 13:23:10.046711

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "dbf604473cee"
down_revision = "f0d460bb5317"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("invoice") as batch_op:
        batch_op.add_column(sa.Column("guests", sa.Integer(), nullable=False))
        # batch_op.drop_constraint("fk_invoice_subscription_id", type_="foreignkey")
        batch_op.drop_column("subscription_id")

    op.add_column("product", sa.Column("guests", sa.Integer(), nullable=False))

    with op.batch_alter_table("subscription") as batch_op:
        batch_op.add_column(sa.Column("invoice_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_subscription_invoice_id", "invoice", ["invoice_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("subscription") as batch_op:
        batch_op.drop_constraint(
            "fk_subscription_invoice_id", "subscription", type_="foreignkey"
        )
        batch_op.drop_column("subscription", "invoice_id")

    op.drop_column("product", "guests")

    with op.batch_alter_table("invoice") as batch_op:
        batch_op.add_column(sa.Column("subscription_id", sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key(
            "fk_invoice_subscription_id", "subscription", ["subscription_id"], ["id"]
        )
        batch_op.drop_column("guests")
