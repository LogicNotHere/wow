from __future__ import annotations

from typing import Self

from wow_shop.shared.contracts import BaseResponseDataModel
from wow_shop.modules.catalog.infrastructure.db.models import ServiceCategory


class CategoryCreatedResponse(BaseResponseDataModel):
    id: int

    @classmethod
    def build(cls, category_id: int) -> Self:
        return cls(id=category_id)


class CategoryListItemResponse(BaseResponseDataModel):
    id: int
    game_id: int
    name: str
    slug: str
    parent_id: int | None
    is_active: bool
    sort_order: int

    @classmethod
    def build(cls, category: ServiceCategory) -> Self:
        return cls(
            id=category.id,
            game_id=category.game_id,
            name=category.name,
            slug=category.slug,
            parent_id=category.parent_id,
            is_active=category.is_active,
            sort_order=category.sort_order,
        )
