from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

from wow_shop.shared.contracts import BaseRequestModel

GameName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]
GameSlug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class CreateGameRequest(BaseRequestModel):
    name: GameName
    slug: GameSlug
    is_active: bool = True
    sort_order: int = 0
