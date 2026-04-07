from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Self

from wow_shop.shared.contracts import BaseResponseDataModel
from wow_shop.modules.pricing.application.pricing_service import (
    PromotionContextItem,
)
from wow_shop.modules.pricing.infrastructure.db.models import (
    PersonalPromotionAssignment,
    Promotion,
    PromotionAudience,
    PromotionBadgeTag,
    PromotionDiscountType,
)


class PromotionCreatedResponse(BaseResponseDataModel):
    id: int

    @classmethod
    def build(cls, promotion_id: int) -> Self:
        return cls(id=promotion_id)


class PromotionListItemResponse(BaseResponseDataModel):
    id: int
    is_enabled: bool
    audience: PromotionAudience

    lot_id: int | None
    category_id: int | None

    discount_type: PromotionDiscountType | None
    discount_percent_value: int | None
    discount_amount_eur: Decimal | None

    badge_tag: PromotionBadgeTag | None
    display_priority: int

    starts_at: datetime | None
    ends_at: datetime | None

    @classmethod
    def build(cls, promotion: Promotion) -> Self:
        return cls(
            id=promotion.id,
            is_enabled=promotion.is_enabled,
            audience=promotion.audience,
            lot_id=promotion.lot_id,
            category_id=promotion.category_id,
            discount_type=promotion.discount_type,
            discount_percent_value=promotion.discount_percent_value,
            discount_amount_eur=promotion.discount_amount_eur,
            badge_tag=promotion.badge_tag,
            display_priority=promotion.display_priority,
            starts_at=promotion.starts_at,
            ends_at=promotion.ends_at,
        )


class PromotionListMetaResponse(BaseResponseDataModel):
    limit: int
    offset: int
    total: int

    @classmethod
    def build(
        cls,
        *,
        limit: int,
        offset: int,
        total: int,
    ) -> Self:
        return cls(
            limit=limit,
            offset=offset,
            total=total,
        )


class PromotionDetailResponse(BaseResponseDataModel):
    id: int
    is_enabled: bool
    audience: PromotionAudience
    starts_at: datetime | None
    ends_at: datetime | None

    lot_id: int | None
    category_id: int | None

    discount_type: PromotionDiscountType | None
    discount_percent_value: int | None
    discount_amount_eur: Decimal | None

    badge_tag: PromotionBadgeTag | None
    display_priority: int

    @classmethod
    def build(cls, promotion: Promotion) -> Self:
        return cls(
            id=promotion.id,
            is_enabled=promotion.is_enabled,
            audience=promotion.audience,
            starts_at=promotion.starts_at,
            ends_at=promotion.ends_at,
            lot_id=promotion.lot_id,
            category_id=promotion.category_id,
            discount_type=promotion.discount_type,
            discount_percent_value=promotion.discount_percent_value,
            discount_amount_eur=promotion.discount_amount_eur,
            badge_tag=promotion.badge_tag,
            display_priority=promotion.display_priority,
        )


class AssignmentDetailResponse(BaseResponseDataModel):
    id: int
    promotion_id: int
    user_id: int
    is_one_time: bool
    expires_at: datetime | None

    @classmethod
    def build(cls, assignment: PersonalPromotionAssignment) -> Self:
        return cls(
            id=assignment.id,
            promotion_id=assignment.promotion_id,
            user_id=assignment.user_id,
            is_one_time=assignment.is_one_time,
            expires_at=assignment.expires_at,
        )


class PromotionAssignmentResponse(AssignmentDetailResponse):
    pass


class PromotionAssignmentListMetaResponse(BaseResponseDataModel):
    limit: int
    offset: int
    total: int

    @classmethod
    def build(
        cls,
        *,
        limit: int,
        offset: int,
        total: int,
    ) -> Self:
        return cls(
            limit=limit,
            offset=offset,
            total=total,
        )


class PublicPromotionContextItemResponse(BaseResponseDataModel):
    promotion_id: int
    lot_id: int | None
    category_id: int | None
    source: str
    badge_tag: PromotionBadgeTag | None
    discount_type: PromotionDiscountType | None
    discount_percent_value: int | None
    discount_amount_eur: Decimal | None

    @classmethod
    def build(cls, item: PromotionContextItem) -> Self:
        return cls(
            promotion_id=item.promotion.id,
            lot_id=item.promotion.lot_id,
            category_id=item.promotion.category_id,
            source=item.source.name,
            badge_tag=item.promotion.badge_tag,
            discount_type=item.promotion.discount_type,
            discount_percent_value=item.promotion.discount_percent_value,
            discount_amount_eur=item.promotion.discount_amount_eur,
        )
