from __future__ import annotations

from typing import Self

from wow_shop.shared.contracts import BaseResponseDataModel
from wow_shop.modules.catalog.infrastructure.db.models import Game


class GameCreatedResponse(BaseResponseDataModel):
    id: int

    @classmethod
    def build(cls, game_id: int) -> Self:
        return cls(id=game_id)


class GameListItemResponse(BaseResponseDataModel):
    id: int
    name: str
    slug: str
    is_active: bool
    sort_order: int

    @classmethod
    def build(cls, game: Game) -> Self:
        return cls(
            id=game.id,
            name=game.name,
            slug=game.slug,
            is_active=game.is_active,
            sort_order=game.sort_order,
        )
