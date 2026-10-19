"""Custom title and description for every product

Revision ID: 57297f62237a
Revises: e9b2b884612e
Create Date: 2023-05-27 13:17:24.043057

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "57297f62237a"
down_revision = "e08f30ab358c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tour_translation") as batch_op:
        batch_op.add_column(sa.Column("description", sa.String(4096), nullable=True))

    with op.batch_alter_table("product") as batch_op:
        batch_op.add_column(sa.Column("language", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("title", sa.String(length=32), nullable=False))
        batch_op.add_column(
            sa.Column("description", sa.String(length=255), nullable=False)
        )
        batch_op.create_index(
            "ix_product_language_tour", ["language", "tour_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("tour_translation") as batch_op:
        batch_op.drop_column("description")

    with op.batch_alter_table("product") as batch_op:
        batch_op.drop_index("ix_product_language_tour")
        batch_op.drop_column("description")
        batch_op.drop_column("title")
        batch_op.drop_column("language")
