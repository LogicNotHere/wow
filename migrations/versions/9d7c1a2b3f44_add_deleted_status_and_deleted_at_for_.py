"""add deleted status and deleted_at for game/category

Revision ID: 9d7c1a2b3f44
Revises: f6e4b3a8c2d1
Create Date: 2026-04-04 15:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d7c1a2b3f44"
down_revision: Union[str, None] = "f6e4b3a8c2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE catalog_game_status_enum "
        "ADD VALUE IF NOT EXISTS 'DELETED'"
    )
    op.execute(
        "ALTER TYPE catalog_service_category_status_enum "
        "ADD VALUE IF NOT EXISTS 'DELETED'"
    )

    op.add_column(
        "catalog_games",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "catalog_service_categories",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catalog_service_categories", "deleted_at")
    op.drop_column("catalog_games", "deleted_at")

    op.alter_column(
        "catalog_service_categories",
        "status",
        server_default=None,
    )
    op.execute(
        "ALTER TYPE catalog_service_category_status_enum "
        "RENAME TO catalog_service_category_status_enum_old"
    )
    op.execute(
        "CREATE TYPE catalog_service_category_status_enum "
        "AS ENUM ('DRAFT', 'ACTIVE', 'INACTIVE')"
    )
    op.execute(
        """
        ALTER TABLE catalog_service_categories
        ALTER COLUMN status TYPE catalog_service_category_status_enum
        USING (
            CASE
                WHEN status::text = 'DELETED' THEN 'INACTIVE'
                ELSE status::text
            END
        )::catalog_service_category_status_enum
        """
    )
    op.alter_column(
        "catalog_service_categories",
        "status",
        server_default=sa.text(
            "'DRAFT'::catalog_service_category_status_enum"
        ),
    )
    op.execute("DROP TYPE catalog_service_category_status_enum_old")

    op.alter_column(
        "catalog_games",
        "status",
        server_default=None,
    )
    op.execute(
        "ALTER TYPE catalog_game_status_enum "
        "RENAME TO catalog_game_status_enum_old"
    )
    op.execute(
        "CREATE TYPE catalog_game_status_enum "
        "AS ENUM ('DRAFT', 'ACTIVE', 'INACTIVE')"
    )
    op.execute(
        """
        ALTER TABLE catalog_games
        ALTER COLUMN status TYPE catalog_game_status_enum
        USING (
            CASE
                WHEN status::text = 'DELETED' THEN 'INACTIVE'
                ELSE status::text
            END
        )::catalog_game_status_enum
        """
    )
    op.alter_column(
        "catalog_games",
        "status",
        server_default=sa.text("'DRAFT'::catalog_game_status_enum"),
    )
    op.execute("DROP TYPE catalog_game_status_enum_old")
