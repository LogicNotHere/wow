from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from wow_shop.infrastructure.db.session import s
from wow_shop.modules.pricing.api.request.models import (
    CreatePromotionAssignmentRequest,
    CreatePromotionRequest,
    PatchPromotionRequest,
)
from wow_shop.modules.pricing.application.errors import (
    PromotionValidationError,
)
from wow_shop.modules.pricing.application.pricing_service import (
    create_promotion as service_create_promotion,
    create_promotion_assignment as service_create_promotion_assignment,
    delete_promotion_assignment as service_delete_promotion_assignment,
    edit_promotion_bl,
    get_category_for_promotion,
    get_lot_for_promotion,
    get_staff_promotion_assignment_by_id,
    get_staff_promotion_by_id,
    get_target_user_for_promotion,
)
from wow_shop.modules.pricing.infrastructure.db.models import (
    Promotion,
    PersonalPromotionAssignment,
)


async def create_promotion(
    *,
    payload: CreatePromotionRequest,
) -> Promotion:
    if (payload.lot_id is None) == (payload.category_id is None):
        raise PromotionValidationError(
            "Exactly one scope target must be provided: lot_id xor category_id."
        )

    lot = None
    if payload.lot_id is not None:
        lot = await get_lot_for_promotion(lot_id=payload.lot_id)

    category = None
    if payload.category_id is not None:
        category = await get_category_for_promotion(
            category_id=payload.category_id,
        )

    target_user = None
    if payload.target_user_id is not None:
        target_user = await get_target_user_for_promotion(
            user_id=payload.target_user_id,
        )

    return await service_create_promotion(
        audience=payload.audience,
        lot=lot,
        category=category,
        discount_type=payload.discount_type,
        discount_percent_value=payload.discount_percent_value,
        discount_amount_eur=payload.discount_amount_eur,
        badge_tag=payload.badge_tag,
        display_priority=payload.display_priority,
        is_enabled=payload.is_enabled,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        target_user=target_user,
        assignment_expires_at=payload.assignment_expires_at,
    )


async def patch_promotion(
    *,
    promotion_id: int,
    payload: PatchPromotionRequest,
) -> Promotion:
    promotion = await get_staff_promotion_by_id(promotion_id=promotion_id)

    edit_promotion_bl(
        promotion=promotion,
        is_enabled=payload.is_enabled,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        badge_tag=payload.badge_tag,
        display_priority=payload.display_priority,
        discount_percent_value=payload.discount_percent_value,
        discount_amount_eur=payload.discount_amount_eur,
    )

    try:
        await s.db.flush()
    except IntegrityError as exc:
        raise PromotionValidationError(
            "Cannot update promotion with provided data."
        ) from exc

    return promotion


async def create_promotion_assignment(
    *,
    promotion_id: int,
    payload: CreatePromotionAssignmentRequest,
) -> PersonalPromotionAssignment:
    promotion = await get_staff_promotion_by_id(promotion_id=promotion_id)
    target_user = await get_target_user_for_promotion(user_id=payload.user_id)
    return await service_create_promotion_assignment(
        promotion=promotion,
        target_user=target_user,
        expires_at=payload.expires_at,
    )


async def delete_promotion_assignment(
    *,
    promotion_id: int,
    assignment_id: int,
) -> PersonalPromotionAssignment:
    promotion = await get_staff_promotion_by_id(promotion_id=promotion_id)
    assignment = await get_staff_promotion_assignment_by_id(
        promotion=promotion,
        assignment_id=assignment_id,
    )
    await service_delete_promotion_assignment(
        promotion=promotion,
        assignment=assignment,
    )
    return assignment
