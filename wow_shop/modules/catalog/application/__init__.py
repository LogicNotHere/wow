"""Catalog application layer."""

from wow_shop.modules.catalog.application.category_service import (
    create_category,
    list_categories,
)
from wow_shop.modules.catalog.application.game_service import (
    create_game,
    list_games,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogError,
    CatalogValidationError,
    ParentCategoryNotFoundError,
    CategoryAlreadyExistsError,
    GameNotFoundError,
    GameAlreadyExistsError,
)

__all__ = [
    "CatalogError",
    "CatalogValidationError",
    "ParentCategoryNotFoundError",
    "CategoryAlreadyExistsError",
    "GameNotFoundError",
    "GameAlreadyExistsError",
    "create_category",
    "create_game",
    "list_games",
    "list_categories",
]
