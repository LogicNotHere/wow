"""replace lot is_active with status lifecycle fields

Revision ID: c3a9f98b1d2e
Revises: 6b2c4cb08c11
Create Date: 2026-03-30 22:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3a9f98b1d2e"
down_revision: Union[str, None] = "6b2c4cb08c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    lot_status_enum = sa.Enum(
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
        "DELETED",
        name="catalog_service_lot_status_enum",
    )
    lot_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "catalog_service_lots",
        sa.Column("status", lot_status_enum, nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_service_lots
        SET status = CASE
            WHEN is_active IS TRUE
                THEN 'ACTIVE'::catalog_service_lot_status_enum
            ELSE 'INACTIVE'::catalog_service_lot_status_enum
        END
        """
    )
    op.alter_column(
        "catalog_service_lots",
        "status",
        existing_type=lot_status_enum,
        nullable=False,
        server_default=sa.text("'DRAFT'::catalog_service_lot_status_enum"),
    )
    op.add_column(
        "catalog_service_lots",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_column("catalog_service_lots", "is_active")


def downgrade() -> None:
    op.add_column(
        "catalog_service_lots",
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_service_lots
        SET is_active = CASE
            WHEN status = 'ACTIVE'::catalog_service_lot_status_enum
                THEN TRUE
            ELSE FALSE
        END
        """
    )
    op.alter_column(
        "catalog_service_lots",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )

    op.drop_column("catalog_service_lots", "deleted_at")
    op.drop_column("catalog_service_lots", "status")

    bind = op.get_bind()
    lot_status_enum = sa.Enum(
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
        "DELETED",
        name="catalog_service_lot_status_enum",
    )
    lot_status_enum.drop(bind, checkfirst=True)
