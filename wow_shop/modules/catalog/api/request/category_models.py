from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from wow_shop.shared.contracts import BaseRequestModel

CategoryName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]
CategorySlug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class CreateCategoryRequest(BaseRequestModel):
    game_id: int = Field(ge=1)
    name: CategoryName
    slug: CategorySlug
    parent_id: int | None = Field(default=None, ge=1)
    is_active: bool = True
    sort_order: int = 0
