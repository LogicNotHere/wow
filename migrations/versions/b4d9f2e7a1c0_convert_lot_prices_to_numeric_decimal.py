"""convert lot prices to numeric decimal

Revision ID: b4d9f2e7a1c0
Revises: 9d7c1a2b3f44
Create Date: 2026-04-07 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4d9f2e7a1c0"
down_revision: Union[str, None] = "9d7c1a2b3f44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "catalog_service_lots",
        "base_price_eur",
        existing_type=sa.Float(),
        type_=sa.Numeric(10, 2),
        postgresql_using="base_price_eur::numeric(10,2)",
        existing_nullable=False,
    )
    op.alter_column(
        "catalog_lot_option_values",
        "price_value",
        existing_type=sa.Float(),
        type_=sa.Numeric(10, 2),
        postgresql_using="price_value::numeric(10,2)",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "catalog_lot_option_values",
        "price_value",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Float(),
        postgresql_using="price_value::double precision",
        existing_nullable=False,
    )
    op.alter_column(
        "catalog_service_lots",
        "base_price_eur",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Float(),
        postgresql_using="base_price_eur::double precision",
        existing_nullable=False,
    )
