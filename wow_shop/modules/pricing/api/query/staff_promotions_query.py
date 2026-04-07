from __future__ import annotations

from fastapi import Depends, Query

from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.modules.pricing.api.query.staff_promotions_filters import (
    StaffPromotionsFilters,
    get_staff_promotions_filters,
)
from wow_shop.modules.pricing.application.pricing_service import (
    StaffPromotionsListResult,
    list_staff_promotions,
)


class GetStaffPromotionsQueryModel(BaseRequestModel):
    filters: StaffPromotionsFilters
    limit: int = 20
    offset: int = 0

    async def get_items(self) -> StaffPromotionsListResult:
        return await list_staff_promotions(
            query_filters=self.filters.to_query_filters(),
            limit=self.limit,
            offset=self.offset,
        )


def get_staff_promotions_query_model(
    filters: StaffPromotionsFilters = Depends(get_staff_promotions_filters),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> GetStaffPromotionsQueryModel:
    return GetStaffPromotionsQueryModel(
        filters=filters,
        limit=limit,
        offset=offset,
    )
