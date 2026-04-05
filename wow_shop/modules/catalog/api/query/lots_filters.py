from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal

from fastapi import Query
from pydantic import StringConstraints

from wow_shop.modules.catalog.application.query_filters import (
    ApplicableFilter,
    ExactFilter,
    SearchILikeFilter,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    ServiceCategory,
    ServiceLot,
    ServiceLotStatus,
)
from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.types import IntId

SearchQuery = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class StaffLotsFilters(BaseRequestModel):
    status: ServiceLotStatus | Literal["all"] | None = None
    game_id: IntId | None = None
    category_id: IntId | None = None
    search: SearchQuery | None = None

    def to_query_filters(self) -> Sequence[ApplicableFilter]:
        resolved_status = None if self.status == "all" else self.status
        return [
            ExactFilter(
                field=ServiceLot.status,
                value=resolved_status,
            ),
            ExactFilter(
                field=ServiceCategory.game_id,
                value=self.game_id,
            ),
            ExactFilter(
                field=ServiceLot.category_id,
                value=self.category_id,
            ),
            SearchILikeFilter(
                fields=(ServiceLot.name, ServiceLot.slug),
                value=self.search,
            ),
        ]


def get_staff_lots_filters(
    status: ServiceLotStatus | Literal["all"] | None = Query(default=None),
    game_id: IntId | None = Query(default=None),
    category_id: IntId | None = Query(default=None),
    search: SearchQuery | None = Query(default=None),
) -> StaffLotsFilters:
    return StaffLotsFilters(
        status=status,
        game_id=game_id,
        category_id=category_id,
        search=search,
    )
