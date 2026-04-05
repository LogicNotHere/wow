"""add slug to catalog service lots

Revision ID: a1f4c3d9b2e1
Revises: 87b2e76f5f71
Create Date: 2026-03-28 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1f4c3d9b2e1"
down_revision: Union[str, None] = "87b2e76f5f71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catalog_service_lots",
        sa.Column("slug", sa.String(length=255), nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_service_lots
        SET slug = COALESCE(
            NULLIF(
                trim(
                    both '-' from regexp_replace(
                        lower(name),
                        '[^a-z0-9]+',
                        '-',
                        'g'
                    )
                ),
                ''
            ),
            'lot-' || id::text
        )
        WHERE slug IS NULL
        """
    )
    op.alter_column(
        "catalog_service_lots",
        "slug",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.create_unique_constraint(
        op.f("uq_catalog_service_lots__category_id_slug"),
        "catalog_service_lots",
        ["category_id", "slug"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_catalog_service_lots__category_id_slug"),
        "catalog_service_lots",
        type_="unique",
    )
    op.drop_column("catalog_service_lots", "slug")
