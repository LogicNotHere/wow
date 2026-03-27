"""Catalog API layer."""

from wow_shop.modules.catalog.api.request import (
    CreateCategoryRequest,
    CreateGameRequest,
)
from wow_shop.modules.catalog.api.response import (
    CategoryCreatedResponse,
    CategoryListItemResponse,
    GameCreatedResponse,
    GameListItemResponse,
)
from wow_shop.modules.catalog.api.routes import public_router, staff_router

__all__ = [
    "CategoryCreatedResponse",
    "CategoryListItemResponse",
    "CreateCategoryRequest",
    "CreateGameRequest",
    "GameCreatedResponse",
    "GameListItemResponse",
    "public_router",
    "staff_router",
]
