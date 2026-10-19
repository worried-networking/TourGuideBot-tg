"""Rename BoughtTours to Subscription

Revision ID: b44bd4455523
Revises: 48cb920beb31
Create Date: 2023-05-18 18:34:40.180348

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b44bd4455523"
down_revision = "48cb920beb31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_bought_tours_guest_id", table_name="bought_tours")
    op.drop_index("ix_bought_tours_is_user_notified", table_name="bought_tours")

    op.rename_table("bought_tours", "subscription")

    op.create_index(
        op.f("ix_subscription_guest_id"), "subscription", ["guest_id"], unique=False
    )
    op.create_index(
        op.f("ix_subscription_is_user_notified"),
        "subscription",
        ["is_user_notified"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_subscription_is_user_notified"), table_name="subscription")
    op.drop_index(op.f("ix_subscription_guest_id"), table_name="subscription")

    op.rename_table("subscription", "bought_tours")

    op.create_index(
        "ix_bought_tours_is_user_notified",
        "bought_tours",
        ["is_user_notified"],
        unique=False,
    )
    op.create_index(
        "ix_bought_tours_guest_id", "bought_tours", ["guest_id"], unique=False
    )
