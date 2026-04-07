from __future__ import annotations

from fastapi import Path, Query

from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.types import IntId
from wow_shop.modules.pricing.application.pricing_service import (
    PromotionAssignmentState,
    StaffPromotionAssignmentsListResult,
    list_staff_promotion_assignments,
)


class GetStaffPromotionAssignmentsQueryModel(BaseRequestModel):
    promotion_id: IntId
    state: PromotionAssignmentState | None = None
    limit: int = 20
    offset: int = 0

    async def get_items(self) -> StaffPromotionAssignmentsListResult:
        return await list_staff_promotion_assignments(
            promotion_id=self.promotion_id,
            state=self.state,
            limit=self.limit,
            offset=self.offset,
        )


def get_staff_promotion_assignments_query_model(
    promotion_id: IntId = Path(),
    state: PromotionAssignmentState | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> GetStaffPromotionAssignmentsQueryModel:
    return GetStaffPromotionAssignmentsQueryModel(
        promotion_id=promotion_id,
        state=state,
        limit=limit,
        offset=offset,
    )
