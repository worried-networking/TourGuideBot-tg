"""Initial version for payment-related tables

Revision ID: 38c070a2b289
Revises: e3a388ce08d0
Create Date: 2023-05-19 22:21:40.418013

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "38c070a2b289"
down_revision = "e3a388ce08d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_provider",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column(
            "created_ts",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_ts", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_provider_language_enabled",
        "payment_provider",
        ["language", "enabled"],
        unique=False,
    )
    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tour_id", sa.Integer(), nullable=False),
        sa.Column("payment_provider_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column(
            "created_ts",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_ts", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["payment_provider_id"],
            ["payment_provider.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tour_id"],
            ["tour.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "invoice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("tour_id", sa.Integer(), nullable=False),
        sa.Column("payment_provider_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_ts",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_ts", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["payment_provider_id"],
            ["payment_provider.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscription.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tour_id"],
            ["tour.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("invoice")
    op.drop_table("product")
    op.drop_index("ix_payment_provider_language_enabled", table_name="payment_provider")
    op.drop_table("payment_provider")
