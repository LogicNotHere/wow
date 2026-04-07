"""add public promotion scope unique indexes

Revision ID: 1c7a9f4d2e11
Revises: b4d9f2e7a1c0
Create Date: 2026-04-07 13:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c7a9f4d2e11"
down_revision: Union[str, None] = "b4d9f2e7a1c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_pricing_promotions__public_lot_id",
        "pricing_promotions",
        ["lot_id"],
        unique=True,
        postgresql_where=sa.text("audience = 'PUBLIC' AND lot_id IS NOT NULL"),
    )
    op.create_index(
        "uq_pricing_promotions__public_category_id",
        "pricing_promotions",
        ["category_id"],
        unique=True,
        postgresql_where=sa.text(
            "audience = 'PUBLIC' AND category_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_pricing_promotions__public_category_id",
        table_name="pricing_promotions",
    )
    op.drop_index(
        "uq_pricing_promotions__public_lot_id",
        table_name="pricing_promotions",
    )
