from __future__ import annotations

from typing import Self

from wow_shop.shared.contracts import BaseResponseDataModel
from wow_shop.modules.catalog.infrastructure.db.models import (
    ServiceCategory,
    ServiceCategoryStatus,
)


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
    status: ServiceCategoryStatus
    sort_order: int

    @classmethod
    def build(cls, category: ServiceCategory) -> Self:
        return cls(
            id=category.id,
            game_id=category.game_id,
            name=category.name,
            slug=category.slug,
            parent_id=category.parent_id,
            status=category.status,
            sort_order=category.sort_order,
        )


class CategoryTreeItemResponse(BaseResponseDataModel):
    id: int
    game_id: int
    name: str
    slug: str
    parent_id: int | None
    status: ServiceCategoryStatus
    sort_order: int
    children: list["CategoryTreeItemResponse"]

    @classmethod
    def build(cls, category: ServiceCategory) -> Self:
        return cls(
            id=category.id,
            game_id=category.game_id,
            name=category.name,
            slug=category.slug,
            parent_id=category.parent_id,
            status=category.status,
            sort_order=category.sort_order,
            children=[],
        )


def build_category_tree(
    categories: list[ServiceCategory],
) -> list[CategoryTreeItemResponse]:
    nodes_by_id = {
        category.id: CategoryTreeItemResponse.build(category)
        for category in categories
    }
    roots: list[CategoryTreeItemResponse] = []

    for category in categories:
        node = nodes_by_id[category.id]
        if category.parent_id is None:
            roots.append(node)
            continue

        parent = nodes_by_id.get(category.parent_id)
        if parent is None:
            roots.append(node)
            continue
        parent.children.append(node)

    def sort_nodes(
        nodes: list[CategoryTreeItemResponse],
    ) -> None:
        nodes.sort(key=lambda item: (item.sort_order, item.id))
        for child in nodes:
            sort_nodes(child.children)

    sort_nodes(roots)
    return roots


CategoryTreeItemResponse.model_rebuild()
