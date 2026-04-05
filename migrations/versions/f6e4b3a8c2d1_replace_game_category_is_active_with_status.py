"""replace game/category is_active with status

Revision ID: f6e4b3a8c2d1
Revises: c3a9f98b1d2e
Create Date: 2026-03-30 22:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6e4b3a8c2d1"
down_revision: Union[str, None] = "c3a9f98b1d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    game_status_enum = sa.Enum(
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
        name="catalog_game_status_enum",
    )
    game_status_enum.create(bind, checkfirst=True)

    category_status_enum = sa.Enum(
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
        name="catalog_service_category_status_enum",
    )
    category_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "catalog_games",
        sa.Column("status", game_status_enum, nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_games
        SET status = CASE
            WHEN is_active IS TRUE
                THEN 'ACTIVE'::catalog_game_status_enum
            ELSE 'INACTIVE'::catalog_game_status_enum
        END
        """
    )
    op.alter_column(
        "catalog_games",
        "status",
        existing_type=game_status_enum,
        nullable=False,
        server_default=sa.text("'DRAFT'::catalog_game_status_enum"),
    )
    op.drop_column("catalog_games", "is_active")

    op.add_column(
        "catalog_service_categories",
        sa.Column("status", category_status_enum, nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_service_categories
        SET status = CASE
            WHEN is_active IS TRUE
                THEN 'ACTIVE'::catalog_service_category_status_enum
            ELSE 'INACTIVE'::catalog_service_category_status_enum
        END
        """
    )
    op.alter_column(
        "catalog_service_categories",
        "status",
        existing_type=category_status_enum,
        nullable=False,
        server_default=sa.text("'DRAFT'::catalog_service_category_status_enum"),
    )
    op.drop_column("catalog_service_categories", "is_active")


def downgrade() -> None:
    op.add_column(
        "catalog_service_categories",
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_service_categories
        SET is_active = CASE
            WHEN status = 'ACTIVE'::catalog_service_category_status_enum
                THEN TRUE
            ELSE FALSE
        END
        """
    )
    op.alter_column(
        "catalog_service_categories",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    op.drop_column("catalog_service_categories", "status")

    op.add_column(
        "catalog_games",
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_games
        SET is_active = CASE
            WHEN status = 'ACTIVE'::catalog_game_status_enum
                THEN TRUE
            ELSE FALSE
        END
        """
    )
    op.alter_column(
        "catalog_games",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    op.drop_column("catalog_games", "status")

    bind = op.get_bind()
    category_status_enum = sa.Enum(
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
        name="catalog_service_category_status_enum",
    )
    category_status_enum.drop(bind, checkfirst=True)

    game_status_enum = sa.Enum(
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
        name="catalog_game_status_enum",
    )
    game_status_enum.drop(bind, checkfirst=True)
