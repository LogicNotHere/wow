from __future__ import annotations

from collections.abc import Sequence

from fastapi import Query

from wow_shop.modules.catalog.application.query_filters import (
    ApplicableFilter,
    ClauseFilter,
    ExactFilter,
)
from wow_shop.modules.pricing.application.pricing_service import (
    PromotionStaffScope,
    PromotionStaffState,
    _build_staff_category_slug_filter,
    _build_staff_lot_slug_filter,
    _build_staff_scope_filter,
    _build_staff_state_filter,
)
from wow_shop.modules.pricing.infrastructure.db.models import (
    Promotion,
    PromotionAudience,
    PromotionBadgeTag,
)
from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.utils.time import now_utc


class StaffPromotionsFilters(BaseRequestModel):
    lot_slug: str | None = None
    category_slug: str | None = None
    state: PromotionStaffState | None = None
    audience: PromotionAudience | None = None
    scope: PromotionStaffScope | None = None
    badge_tag: PromotionBadgeTag | None = None

    def to_query_filters(self) -> Sequence[ApplicableFilter]:
        now = now_utc()
        return [
            ExactFilter(
                field=Promotion.audience,
                value=self.audience,
            ),
            ExactFilter(
                field=Promotion.badge_tag,
                value=self.badge_tag,
            ),
            ClauseFilter(
                clause=_build_staff_scope_filter(scope=self.scope),
            ),
            ClauseFilter(
                clause=(
                    _build_staff_state_filter(
                        state=self.state,
                        now=now,
                    )
                    if self.state is not None
                    else None
                ),
            ),
            ClauseFilter(
                clause=(
                    _build_staff_lot_slug_filter(lot_slug=self.lot_slug)
                    if self.lot_slug is not None
                    else None
                ),
            ),
            ClauseFilter(
                clause=(
                    _build_staff_category_slug_filter(
                        category_slug=self.category_slug
                    )
                    if self.category_slug is not None
                    else None
                ),
            ),
        ]


def get_staff_promotions_filters(
    lot_slug: str | None = Query(default=None),
    category_slug: str | None = Query(default=None),
    state: PromotionStaffState | None = Query(default=None),
    audience: PromotionAudience | None = Query(default=None),
    scope: PromotionStaffScope | None = Query(default=None),
    badge_tag: PromotionBadgeTag | None = Query(default=None),
) -> StaffPromotionsFilters:
    return StaffPromotionsFilters(
        lot_slug=lot_slug,
        category_slug=category_slug,
        state=state,
        audience=audience,
        scope=scope,
        badge_tag=badge_tag,
    )
