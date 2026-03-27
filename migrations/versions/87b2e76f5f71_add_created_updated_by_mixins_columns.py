"""add created_by/updated_by columns for mixin adoption

Revision ID: 87b2e76f5f71
Revises: 5805f3f173f4
Create Date: 2026-03-27 13:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "87b2e76f5f71"
down_revision: Union[str, None] = "5805f3f173f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CREATED_BY_TABLES = (
    "auth_users",
    "auth_booster_profiles",
    "auth_admin_notes",
    "catalog_service_lots",
    "catalog_service_pages",
    "catalog_service_page_blocks",
    "orders_guest_contacts",
    "orders_orders",
    "orders_magic_links",
    "orders_order_claims",
    "chat_threads",
    "chat_messages",
    "payments_payments",
    "payments_refunds",
    "notifications_system_notifications",
    "notifications_in_app_notifications",
)

UPDATED_BY_TABLES = (
    "auth_booster_profiles",
    "catalog_service_lots",
    "catalog_service_pages",
    "catalog_service_page_blocks",
    "orders_orders",
)


def _add_user_ref_column(table_name: str, column_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column(column_name, sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        op.f(f"fk_{table_name}__{column_name}__auth_users"),
        table_name,
        "auth_users",
        [column_name],
        ["id"],
    )


def _drop_user_ref_column(table_name: str, column_name: str) -> None:
    op.drop_constraint(
        op.f(f"fk_{table_name}__{column_name}__auth_users"),
        table_name,
        type_="foreignkey",
    )
    op.drop_column(table_name, column_name)


def upgrade() -> None:
    for table_name in CREATED_BY_TABLES:
        _add_user_ref_column(table_name, "created_by_user_id")

    for table_name in UPDATED_BY_TABLES:
        _add_user_ref_column(table_name, "updated_by_user_id")


def downgrade() -> None:
    for table_name in reversed(UPDATED_BY_TABLES):
        _drop_user_ref_column(table_name, "updated_by_user_id")

    for table_name in reversed(CREATED_BY_TABLES):
        _drop_user_ref_column(table_name, "created_by_user_id")

