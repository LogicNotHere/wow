from __future__ import annotations

from decimal import Decimal
from datetime import datetime

from pydantic import Field

from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.pydantic import PartialModel
from wow_shop.shared.types import IntId
from wow_shop.modules.pricing.infrastructure.db.models import (
    PromotionAudience,
    PromotionBadgeTag,
    PromotionDiscountType,
)


class CreatePromotionRequest(BaseRequestModel):
    audience: PromotionAudience = PromotionAudience.PUBLIC
    lot_id: IntId | None = None
    category_id: IntId | None = None

    discount_type: PromotionDiscountType | None = None
    discount_percent_value: int | None = None
    discount_amount_eur: Decimal | None = None

    badge_tag: PromotionBadgeTag | None = None
    display_priority: int = 0

    is_enabled: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    target_user_id: IntId | None = None
    assignment_expires_at: datetime | None = None


class CreatePromotionAssignmentRequest(BaseRequestModel):
    user_id: IntId
    expires_at: datetime


class PromotionPatchFieldsRequest(BaseRequestModel):
    is_enabled: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    badge_tag: PromotionBadgeTag | None = None
    display_priority: int = Field(ge=0)
    discount_percent_value: int
    discount_amount_eur: Decimal


@PartialModel()
class PatchPromotionRequest(PromotionPatchFieldsRequest):
    pass
