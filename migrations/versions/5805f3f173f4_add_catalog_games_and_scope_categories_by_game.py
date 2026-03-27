"""add catalog games and scope categories by game

Revision ID: 5805f3f173f4
Revises: ba9390fe80ac
Create Date: 2026-03-26 16:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5805f3f173f4"
down_revision: Union[str, None] = "ba9390fe80ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_games")),
        sa.UniqueConstraint("slug", name=op.f("uq_catalog_games__slug")),
    )

    op.add_column(
        "catalog_service_categories",
        sa.Column("game_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_catalog_service_categories__game_id__catalog_games"),
        "catalog_service_categories",
        "catalog_games",
        ["game_id"],
        ["id"],
    )

    # Dev-stage pragmatic backfill strategy:
    # create one default game and map all existing categories to it.
    op.execute(
        """
        INSERT INTO catalog_games (name, slug, is_active, sort_order)
        VALUES ('World of Warcraft', 'world-of-warcraft', true, 0)
        """
    )
    op.execute(
        """
        UPDATE catalog_service_categories
        SET game_id = (
            SELECT id
            FROM catalog_games
            WHERE slug = 'world-of-warcraft'
            LIMIT 1
        )
        WHERE game_id IS NULL
        """
    )

    op.alter_column(
        "catalog_service_categories",
        "game_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_constraint(
        op.f("uq_catalog_service_categories__parent_id_slug"),
        "catalog_service_categories",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_catalog_service_categories__game_id_parent_id_slug"),
        "catalog_service_categories",
        ["game_id", "parent_id", "slug"],
    )
    op.create_index(
        "uq_catalog_service_categories__game_id_slug__root",
        "catalog_service_categories",
        ["game_id", "slug"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        op.f("ix_catalog_service_categories__game_id"),
        "catalog_service_categories",
        ["game_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_catalog_service_categories__game_id"),
        table_name="catalog_service_categories",
    )
    op.drop_index(
        "uq_catalog_service_categories__game_id_slug__root",
        table_name="catalog_service_categories",
    )
    op.drop_constraint(
        op.f("uq_catalog_service_categories__game_id_parent_id_slug"),
        "catalog_service_categories",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_catalog_service_categories__parent_id_slug"),
        "catalog_service_categories",
        ["parent_id", "slug"],
    )

    op.drop_constraint(
        op.f("fk_catalog_service_categories__game_id__catalog_games"),
        "catalog_service_categories",
        type_="foreignkey",
    )
    op.drop_column("catalog_service_categories", "game_id")
    op.drop_table("catalog_games")
