from __future__ import annotations

from typing import Any

from sqlalchemy.sql import Select

from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServiceLotStatus,
    ServicePage,
    ServicePageStatus,
)


def apply_public_lot_visibility(query: Select[Any]) -> Select[Any]:
    """Apply visibility rules for public lot read flows."""

    return query.where(
        ServiceLot.status == ServiceLotStatus.ACTIVE,
        ServiceCategory.status == ServiceCategoryStatus.ACTIVE,
        Game.status == GameStatus.ACTIVE,
        ServicePage.status == ServicePageStatus.PUBLISHED,
    )
