from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.pydantic.partial import PartialModel
from wow_shop.shared.types import IntId
from wow_shop.modules.catalog.infrastructure.db.models import GameStatus

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


class GameCommonRequest(BaseRequestModel):
    name: GameName
    slug: GameSlug
    status: GameStatus = GameStatus.ACTIVE
    sort_order: int = Field(default=0, ge=0)


class CreateGameRequest(GameCommonRequest):
    pass


@PartialModel()
class PatchGameRequest(GameCommonRequest):
    pass


class ReorderGamesRequest(BaseRequestModel):
    ids: list[IntId]
