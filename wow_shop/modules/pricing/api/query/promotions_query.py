from __future__ import annotations

from fastapi import Query

from wow_shop.shared.auth.context import get_auth_user_id
from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.types import IntId
from wow_shop.modules.pricing.application.pricing_service import (
    PromotionContextScope,
    PromotionContextItem,
    get_public_promotions_context,
)
from wow_shop.modules.pricing.infrastructure.db.models import PromotionBadgeTag


class GetPublicPromotionsContextQueryModel(BaseRequestModel):
    lot_ids: list[IntId] | None = None
    category_ids: list[IntId] | None = None
    badge: PromotionBadgeTag | None = None
    scope: PromotionContextScope = PromotionContextScope.ALL
    user_id: IntId | None = None

    async def get_items(self) -> list[PromotionContextItem]:
        return await get_public_promotions_context(
            lot_ids=self.lot_ids,
            category_ids=self.category_ids,
            badge=self.badge,
            user_id=self.user_id,
            scope=self.scope,
        )


def get_public_promotions_context_query_model(
    lot_ids: list[IntId] | None = Query(default=None),
    category_ids: list[IntId] | None = Query(default=None),
    badge: PromotionBadgeTag | None = Query(default=None),
    scope: PromotionContextScope = Query(default=PromotionContextScope.ALL),
) -> GetPublicPromotionsContextQueryModel:
    return GetPublicPromotionsContextQueryModel(
        lot_ids=lot_ids,
        category_ids=category_ids,
        badge=badge,
        scope=scope,
        user_id=get_auth_user_id(),
    )
