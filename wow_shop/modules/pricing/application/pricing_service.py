from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from enum import StrEnum, auto
from collections.abc import Sequence

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.exc import IntegrityError

from wow_shop.infrastructure.db.session import s
from wow_shop.modules.catalog.application.query_filters import (
    ApplicableFilter,
    apply_filters,
)
from wow_shop.modules.auth.infrastructure.db.models import User
from wow_shop.modules.catalog.application.category_service import (
    apply_public_category_visibility,
)
from wow_shop.modules.catalog.application.read_utils import (
    apply_public_lot_visibility,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServicePage,
)
from wow_shop.modules.pricing.application.errors import (
    PromotionAssignmentAlreadyExistsError,
    PromotionAssignmentNotFoundError,
    PromotionCategoryNotFoundError,
    PromotionLotNotFoundError,
    PromotionNotFoundError,
    PromotionTargetUserNotFoundError,
    PromotionValidationError,
)
from wow_shop.modules.pricing.infrastructure.db.models import (
    PersonalPromotionAssignment,
    Promotion,
    PromotionAudience,
    PromotionBadgeTag,
    PromotionDiscountType,
    PromotionUsage,
)
from wow_shop.shared.utils.missing import Missing, MissingType
from wow_shop.shared.utils.time import now_utc


@dataclass(frozen=True)
class PromotionContextItem:
    promotion: Promotion
    source: PromotionAudience


class PromotionContextScope(StrEnum):
    LOT = auto()
    CATEGORY = auto()
    ALL = auto()


class PromotionStaffState(StrEnum):
    ACTIVE = auto()
    SCHEDULED = auto()
    EXPIRED = auto()
    DISABLED = auto()


class PromotionStaffScope(StrEnum):
    LOT = auto()
    CATEGORY = auto()


@dataclass(frozen=True)
class StaffPromotionsListResult:
    items: list[Promotion]
    total: int
    limit: int
    offset: int


class PromotionAssignmentState(StrEnum):
    ACTIVE = auto()
    EXPIRED = auto()
    USED = auto()


@dataclass(frozen=True)
class StaffPromotionAssignmentsListResult:
    items: list[PersonalPromotionAssignment]
    total: int
    limit: int
    offset: int


async def get_staff_promotion_by_id(
    *,
    promotion_id: int,
) -> Promotion:
    promotion_query = (
        select(Promotion)
        .where(Promotion.id == promotion_id)
        .limit(1)
    )
    promotion_result = await s.db.execute(promotion_query)
    promotion = promotion_result.scalar_one_or_none()
    if promotion is None:
        raise PromotionNotFoundError("Promotion not found.")

    return promotion


async def get_staff_promotion_assignments(
    *,
    promotion_id: int,
) -> list[PersonalPromotionAssignment]:
    result = await list_staff_promotion_assignments(
        promotion_id=promotion_id,
        state=None,
        limit=10_000,
        offset=0,
    )
    return result.items


def _build_staff_promotion_assignment_state_filter(
    *,
    state: PromotionAssignmentState,
    now: datetime,
) -> object:
    usage_exists = exists(
        select(PromotionUsage.id)
        .where(
            PromotionUsage.promotion_id
            == PersonalPromotionAssignment.promotion_id
        )
        .where(PromotionUsage.user_id == PersonalPromotionAssignment.user_id)
    )
    if state is PromotionAssignmentState.EXPIRED:
        return and_(
            PersonalPromotionAssignment.expires_at.is_not(None),
            PersonalPromotionAssignment.expires_at < now,
        )
    if state is PromotionAssignmentState.USED:
        return and_(
            PersonalPromotionAssignment.is_one_time.is_(True),
            usage_exists,
        )
    return and_(
        or_(
            PersonalPromotionAssignment.expires_at.is_(None),
            PersonalPromotionAssignment.expires_at >= now,
        ),
        or_(
            PersonalPromotionAssignment.is_one_time.is_(False),
            ~usage_exists,
        ),
    )


def _build_staff_promotion_assignments_base_query(
    *,
    promotion_id: int,
    state: PromotionAssignmentState | None,
    now: datetime,
) -> object:
    query = select(PersonalPromotionAssignment).where(
        PersonalPromotionAssignment.promotion_id == promotion_id
    )
    if state is not None:
        query = query.where(
            _build_staff_promotion_assignment_state_filter(
                state=state,
                now=now,
            )
        )
    return query


async def list_staff_promotion_assignments(
    *,
    promotion_id: int,
    state: PromotionAssignmentState | None,
    limit: int,
    offset: int,
) -> StaffPromotionAssignmentsListResult:
    promotion = await get_staff_promotion_by_id(promotion_id=promotion_id)
    now = now_utc()
    base_query = _build_staff_promotion_assignments_base_query(
        promotion_id=promotion.id,
        state=state,
        now=now,
    )

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await s.db.execute(count_query)
    total = int(total_result.scalar_one())

    items_query = (
        base_query.order_by(PersonalPromotionAssignment.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items_result = await s.db.execute(items_query)
    items = list(items_result.scalars().all())

    return StaffPromotionAssignmentsListResult(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_staff_promotion_assignment_by_id(
    *,
    promotion: Promotion,
    assignment_id: int,
) -> PersonalPromotionAssignment:
    query = (
        select(PersonalPromotionAssignment)
        .where(PersonalPromotionAssignment.id == assignment_id)
        .where(PersonalPromotionAssignment.promotion_id == promotion.id)
        .limit(1)
    )
    result = await s.db.execute(query)
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise PromotionAssignmentNotFoundError("Promotion assignment not found.")
    return assignment


def _build_staff_state_filter(
    *,
    state: PromotionStaffState,
    now: datetime,
) -> object:
    if state is PromotionStaffState.DISABLED:
        return Promotion.is_enabled.is_(False)
    if state is PromotionStaffState.SCHEDULED:
        return and_(
            Promotion.is_enabled.is_(True),
            Promotion.starts_at.is_not(None),
            Promotion.starts_at > now,
        )
    if state is PromotionStaffState.EXPIRED:
        return and_(
            Promotion.is_enabled.is_(True),
            Promotion.ends_at.is_not(None),
            Promotion.ends_at < now,
        )
    return and_(
        Promotion.is_enabled.is_(True),
        or_(Promotion.starts_at.is_(None), Promotion.starts_at <= now),
        or_(Promotion.ends_at.is_(None), Promotion.ends_at >= now),
    )


def _build_staff_lot_slug_filter(*, lot_slug: str) -> object:
    return exists(
        select(ServiceLot.id)
        .where(ServiceLot.id == Promotion.lot_id)
        .where(ServiceLot.slug == lot_slug)
    )


def _build_staff_category_slug_filter(*, category_slug: str) -> object:
    direct_category_match = exists(
        select(ServiceCategory.id)
        .where(ServiceCategory.id == Promotion.category_id)
        .where(ServiceCategory.slug == category_slug)
    )
    lot_category_match = exists(
        select(ServiceLot.id)
        .join(
            ServiceCategory,
            ServiceLot.category_id == ServiceCategory.id,
        )
        .where(ServiceLot.id == Promotion.lot_id)
        .where(ServiceCategory.slug == category_slug)
    )
    return or_(direct_category_match, lot_category_match)


def _build_staff_scope_filter(
    *,
    scope: PromotionStaffScope | None,
) -> object | None:
    if scope is PromotionStaffScope.LOT:
        return Promotion.lot_id.is_not(None)
    if scope is PromotionStaffScope.CATEGORY:
        return Promotion.category_id.is_not(None)
    return None


def _build_staff_promotions_base_query(
    *,
    query_filters: Sequence[ApplicableFilter],
) -> object:
    return apply_filters(
        select(Promotion),
        filters=query_filters,
    )


async def list_staff_promotions(
    *,
    query_filters: Sequence[ApplicableFilter],
    limit: int = 20,
    offset: int = 0,
) -> StaffPromotionsListResult:
    base_query = _build_staff_promotions_base_query(
        query_filters=query_filters,
    )

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await s.db.execute(count_query)
    total = int(total_result.scalar_one())

    items_query = (
        base_query.order_by(Promotion.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items_result = await s.db.execute(items_query)
    items = list(items_result.scalars().all())

    return StaffPromotionsListResult(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def _normalize_ids(ids: list[int] | None) -> list[int]:
    if not ids:
        return []

    unique_ids: list[int] = []
    seen_ids: set[int] = set()
    for item_id in ids:
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        unique_ids.append(item_id)
    return unique_ids


def _validate_public_promotions_context_filters(
    *,
    lot_ids: list[int],
    category_ids: list[int],
    badge: PromotionBadgeTag | None,
) -> None:
    if not lot_ids and not category_ids and badge is None:
        raise PromotionValidationError(
            "At least one filter must be provided: lot_ids, category_ids, or badge."
        )


def _build_promotions_scope_filter(
    *,
    lot_ids: list[int],
    category_ids: list[int],
) -> object | None:
    scope_filters: list[object] = []
    if lot_ids:
        scope_filters.append(Promotion.lot_id.in_(lot_ids))
    if category_ids:
        scope_filters.append(Promotion.category_id.in_(category_ids))
    if not scope_filters:
        return None
    return or_(*scope_filters)


async def _resolve_category_ids_for_lot_scope(
    *,
    lot_ids: list[int],
) -> list[int]:
    if not lot_ids:
        return []

    query = (
        select(ServiceLot.category_id)
        .where(ServiceLot.id.in_(lot_ids))
        .distinct()
        .order_by(ServiceLot.category_id.asc())
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())


def _merge_category_ids(
    *,
    explicit_category_ids: list[int],
    resolved_category_ids: list[int],
) -> list[int]:
    merged_ids: list[int] = []
    seen_ids: set[int] = set()
    for category_id in [*explicit_category_ids, *resolved_category_ids]:
        if category_id in seen_ids:
            continue
        seen_ids.add(category_id)
        merged_ids.append(category_id)
    return merged_ids


def _build_promotions_target_scope_filter(
    *,
    scope: PromotionContextScope,
) -> object | None:
    if scope is PromotionContextScope.ALL:
        return None
    if scope is PromotionContextScope.LOT:
        return Promotion.lot_id.is_not(None)
    return Promotion.category_id.is_not(None)


def _build_promotions_context_filters(
    *,
    now: datetime,
    badge: PromotionBadgeTag | None,
) -> list[object]:
    filters: list[object] = list(_build_active_promotion_filters(now=now))
    if badge is not None:
        filters.append(Promotion.badge_tag == badge)
    return filters


def _build_public_visible_scope_filter() -> object:
    public_visible_lot_ids = apply_public_lot_visibility(
        select(ServiceLot.id)
        .join(
            ServiceCategory,
            ServiceLot.category_id == ServiceCategory.id,
        )
        .join(
            Game,
            ServiceCategory.game_id == Game.id,
        )
        .join(
            ServicePage,
            ServicePage.lot_id == ServiceLot.id,
        )
    )
    public_visible_category_ids = apply_public_category_visibility(
        select(ServiceCategory.id)
        .join(ServiceCategory.game)
        .where(
            ServiceCategory.status == ServiceCategoryStatus.ACTIVE,
            Game.status == GameStatus.ACTIVE,
        )
    )
    return or_(
        Promotion.lot_id.in_(public_visible_lot_ids),
        Promotion.category_id.in_(public_visible_category_ids),
    )


async def _get_public_promotions_context_items(
    *,
    scope_filter: object | None,
    target_scope_filter: object | None,
    context_filters: list[object],
    public_visible_scope_filter: object,
) -> list[PromotionContextItem]:
    query = (
        select(Promotion)
        .where(Promotion.audience == PromotionAudience.PUBLIC)
        .where(
            or_(
                Promotion.category_id.is_(None),
                Promotion.discount_type.is_(None),
            )
        )
        .where(public_visible_scope_filter)
        .where(*context_filters)
    )
    if scope_filter is not None:
        query = query.where(scope_filter)
    if target_scope_filter is not None:
        query = query.where(target_scope_filter)
    query = query.order_by(Promotion.id.asc())

    result = await s.db.execute(query)
    promotions = list(result.scalars().all())
    return [
        PromotionContextItem(
            promotion=promotion,
            source=PromotionAudience.PUBLIC,
        )
        for promotion in promotions
    ]


async def _get_personal_promotions_context_items(
    *,
    user_id: int,
    now: datetime,
    scope_filter: object | None,
    target_scope_filter: object | None,
    context_filters: list[object],
    public_visible_scope_filter: object,
) -> list[PromotionContextItem]:
    used_one_time_promotion_exists = exists(
        select(PromotionUsage.id)
        .where(PromotionUsage.promotion_id == Promotion.id)
        .where(PromotionUsage.user_id == user_id)
    )
    query = (
        select(Promotion)
        .join(
            PersonalPromotionAssignment,
            PersonalPromotionAssignment.promotion_id == Promotion.id,
        )
        .where(Promotion.audience == PromotionAudience.PERSONAL)
        .where(public_visible_scope_filter)
        .where(PersonalPromotionAssignment.user_id == user_id)
        .where(
            or_(
                PersonalPromotionAssignment.expires_at.is_(None),
                PersonalPromotionAssignment.expires_at >= now,
            )
        )
        .where(
            or_(
                PersonalPromotionAssignment.is_one_time.is_(False),
                ~used_one_time_promotion_exists,
            )
        )
        .where(*context_filters)
    )
    if scope_filter is not None:
        query = query.where(scope_filter)
    if target_scope_filter is not None:
        query = query.where(target_scope_filter)
    query = query.order_by(Promotion.id.asc())

    result = await s.db.execute(query)
    promotions = list(result.scalars().all())
    return [
        PromotionContextItem(
            promotion=promotion,
            source=PromotionAudience.PERSONAL,
        )
        for promotion in promotions
    ]


async def get_public_promotions_context(
    *,
    lot_ids: list[int] | None,
    category_ids: list[int] | None,
    badge: PromotionBadgeTag | None,
    user_id: int | None,
    scope: PromotionContextScope,
) -> list[PromotionContextItem]:
    normalized_lot_ids = _normalize_ids(lot_ids)
    normalized_category_ids = _normalize_ids(category_ids)
    resolved_category_ids = await _resolve_category_ids_for_lot_scope(
        lot_ids=normalized_lot_ids
    )
    effective_category_ids = _merge_category_ids(
        explicit_category_ids=normalized_category_ids,
        resolved_category_ids=resolved_category_ids,
    )
    _validate_public_promotions_context_filters(
        lot_ids=normalized_lot_ids,
        category_ids=effective_category_ids,
        badge=badge,
    )

    now = now_utc()
    scope_filter = _build_promotions_scope_filter(
        lot_ids=normalized_lot_ids,
        category_ids=effective_category_ids,
    )
    target_scope_filter = _build_promotions_target_scope_filter(scope=scope)
    public_visible_scope_filter = _build_public_visible_scope_filter()
    context_filters = _build_promotions_context_filters(
        now=now,
        badge=badge,
    )

    items = await _get_public_promotions_context_items(
        scope_filter=scope_filter,
        target_scope_filter=target_scope_filter,
        context_filters=context_filters,
        public_visible_scope_filter=public_visible_scope_filter,
    )
    if user_id is not None:
        items.extend(
            await _get_personal_promotions_context_items(
                user_id=user_id,
                now=now,
                scope_filter=scope_filter,
                target_scope_filter=target_scope_filter,
                context_filters=context_filters,
                public_visible_scope_filter=public_visible_scope_filter,
            )
        )

    return items


def _build_active_promotion_filters(*, now: datetime) -> tuple[object, ...]:
    return (
        Promotion.is_enabled.is_(True),
        or_(Promotion.starts_at.is_(None), Promotion.starts_at <= now),
        or_(Promotion.ends_at.is_(None), Promotion.ends_at >= now),
    )


async def _promotion_assignment_exists(
    *,
    promotion_id: int,
    user_id: int,
) -> bool:
    query = (
        select(PersonalPromotionAssignment.id)
        .where(PersonalPromotionAssignment.promotion_id == promotion_id)
        .where(PersonalPromotionAssignment.user_id == user_id)
        .limit(1)
    )
    result = await s.db.execute(query)
    return result.scalar_one_or_none() is not None


async def _public_promotion_exists_for_lot(
    *,
    lot_id: int,
) -> bool:
    query = (
        select(Promotion.id)
        .where(Promotion.audience == PromotionAudience.PUBLIC)
        .where(Promotion.lot_id == lot_id)
        .limit(1)
    )
    result = await s.db.execute(query)
    return result.scalar_one_or_none() is not None


async def _public_promotion_exists_for_category(
    *,
    category_id: int,
) -> bool:
    query = (
        select(Promotion.id)
        .where(Promotion.audience == PromotionAudience.PUBLIC)
        .where(Promotion.category_id == category_id)
        .limit(1)
    )
    result = await s.db.execute(query)
    return result.scalar_one_or_none() is not None


async def _validate_public_scope_uniqueness(
    *,
    audience: PromotionAudience,
    lot: ServiceLot | None,
    category: ServiceCategory | None,
) -> None:
    if audience is not PromotionAudience.PUBLIC:
        return

    if lot is not None and await _public_promotion_exists_for_lot(
        lot_id=lot.id
    ):
        raise PromotionValidationError(
            "Public promotion for this lot already exists."
        )

    if category is not None and await _public_promotion_exists_for_category(
        category_id=category.id
    ):
        raise PromotionValidationError(
            "Public promotion for this category already exists."
        )


async def _count_promotion_assignments(
    *,
    promotion_id: int,
) -> int:
    query = (
        select(func.count(PersonalPromotionAssignment.id))
        .where(PersonalPromotionAssignment.promotion_id == promotion_id)
    )
    result = await s.db.execute(query)
    return int(result.scalar_one())


def _extract_integrity_constraint_name(exc: IntegrityError) -> str | None:
    original_error = exc.orig
    constraint_name = getattr(original_error, "constraint_name", None)
    if constraint_name is None:
        diag = getattr(original_error, "diag", None)
        constraint_name = getattr(diag, "constraint_name", None)
    return constraint_name


def _is_assignment_scope_conflict(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    if sqlstate != "23505":
        return False

    constraint_name = _extract_integrity_constraint_name(exc)
    expected_constraint = (
        "uq_pricing_personal_promotion_assignments__promotion_id_user_id"
    )
    if constraint_name == expected_constraint:
        return True

    return expected_constraint in str(original_error)


def _is_public_lot_scope_conflict(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    if sqlstate != "23505":
        return False

    expected_constraint = "uq_pricing_promotions__public_lot_id"
    constraint_name = _extract_integrity_constraint_name(exc)
    if constraint_name == expected_constraint:
        return True
    return expected_constraint in str(original_error)


def _is_public_category_scope_conflict(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    if sqlstate != "23505":
        return False

    expected_constraint = "uq_pricing_promotions__public_category_id"
    constraint_name = _extract_integrity_constraint_name(exc)
    if constraint_name == expected_constraint:
        return True
    return expected_constraint in str(original_error)


def _validate_scope(
    *,
    lot: ServiceLot | None,
    category: ServiceCategory | None,
) -> None:
    if (lot is None) == (category is None):
        raise PromotionValidationError(
            "Exactly one scope target must be provided: lot_id xor category_id."
        )


def _validate_discount(
    *,
    discount_type: PromotionDiscountType | None,
    discount_percent_value: int | None,
    discount_amount_eur: Decimal | None,
) -> None:
    if discount_type is PromotionDiscountType.PERCENT:
        if discount_percent_value is None:
            raise PromotionValidationError(
                "discount_percent_value is required for PERCENT discount."
            )
        if discount_amount_eur is not None:
            raise PromotionValidationError(
                "discount_amount_eur must be null for PERCENT discount."
            )
        if discount_percent_value < 0 or discount_percent_value > 100:
            raise PromotionValidationError(
                "discount_percent_value must be between 0 and 100."
            )
        return

    if discount_type is PromotionDiscountType.FIXED_AMOUNT:
        if discount_amount_eur is None:
            raise PromotionValidationError(
                "discount_amount_eur is required for FIXED_AMOUNT discount."
            )
        if discount_percent_value is not None:
            raise PromotionValidationError(
                "discount_percent_value must be null for FIXED_AMOUNT discount."
            )
        if discount_amount_eur < 0:
            raise PromotionValidationError(
                "discount_amount_eur must be greater than or equal to 0."
            )
        return

    if discount_percent_value is not None or discount_amount_eur is not None:
        raise PromotionValidationError(
            "discount_type is required when discount values are provided."
        )


def _validate_not_empty(
    *,
    discount_type: PromotionDiscountType | None,
    badge_tag: PromotionBadgeTag | None,
) -> None:
    if discount_type is None and badge_tag is None:
        raise PromotionValidationError(
            "Promotion must contain discount, badge, or both."
        )


def _validate_activity_window(
    *,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> None:
    if starts_at is not None and ends_at is not None and starts_at > ends_at:
        raise PromotionValidationError(
            "starts_at must be less than or equal to ends_at."
        )


def _validate_display_priority(
    *,
    display_priority: int,
) -> None:
    if display_priority < 0:
        raise PromotionValidationError(
            "display_priority must be greater than or equal to 0."
        )


def _validate_promotion_state(
    *,
    audience: PromotionAudience,
    category_id: int | None,
    discount_type: PromotionDiscountType | None,
    discount_percent_value: int | None,
    discount_amount_eur: Decimal | None,
    badge_tag: PromotionBadgeTag | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> None:
    _validate_discount(
        discount_type=discount_type,
        discount_percent_value=discount_percent_value,
        discount_amount_eur=discount_amount_eur,
    )
    _validate_not_empty(
        discount_type=discount_type,
        badge_tag=badge_tag,
    )
    _validate_activity_window(starts_at=starts_at, ends_at=ends_at)
    if (
        audience is PromotionAudience.PUBLIC
        and category_id is not None
        and discount_type is not None
    ):
        raise PromotionValidationError(
            "Public category promotion cannot contain pricing discount."
        )


def _validate_promotion_allows_personal_usage(*, promotion: Promotion) -> None:
    if promotion.audience is not PromotionAudience.PERSONAL:
        raise PromotionValidationError(
            "Assignments are allowed only for PERSONAL promotions."
        )
    if promotion.discount_type is None:
        raise PromotionValidationError(
            "Personal assignment is allowed only for promotions with discount."
        )


def _validate_personal_assignment(
    *,
    audience: PromotionAudience,
    discount_type: PromotionDiscountType | None,
    target_user: User | None,
    assignment_expires_at: datetime | None,
) -> None:
    if audience is PromotionAudience.PERSONAL:
        if discount_type is None:
            raise PromotionValidationError(
                "Personal promotion must contain discount."
            )
        if target_user is None:
            raise PromotionValidationError(
                "target_user_id is required for personal promotion."
            )
        if assignment_expires_at is None:
            raise PromotionValidationError(
                "assignment_expires_at is required for personal promotion."
            )
        return

    if target_user is not None or assignment_expires_at is not None:
        raise PromotionValidationError(
            "Personal assignment fields are allowed only for PERSONAL promotions."
        )


async def create_promotion_assignment(
    *,
    promotion: Promotion,
    target_user: User,
    expires_at: datetime,
) -> PersonalPromotionAssignment:
    _validate_promotion_allows_personal_usage(promotion=promotion)

    if await _promotion_assignment_exists(
        promotion_id=promotion.id,
        user_id=target_user.id,
    ):
        raise PromotionAssignmentAlreadyExistsError(
            "Promotion assignment for this user already exists."
        )

    assignment = PersonalPromotionAssignment(
        promotion_id=promotion.id,
        user_id=target_user.id,
        is_one_time=True,
        expires_at=expires_at,
    )
    s.db.add(assignment)
    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_assignment_scope_conflict(exc):
            raise PromotionAssignmentAlreadyExistsError(
                "Promotion assignment for this user already exists."
            ) from exc
        raise

    return assignment


async def delete_promotion_assignment(
    *,
    promotion: Promotion,
    assignment: PersonalPromotionAssignment,
) -> None:
    if promotion.audience is PromotionAudience.PERSONAL:
        assignments_count = await _count_promotion_assignments(
            promotion_id=promotion.id,
        )
        if assignments_count <= 1:
            raise PromotionValidationError(
                "Cannot delete the last assignment for PERSONAL promotion."
            )

    await s.db.delete(assignment)
    await s.db.flush()


def edit_promotion_bl(
    *,
    promotion: Promotion,
    is_enabled: bool | None | MissingType,
    starts_at: datetime | None | MissingType,
    ends_at: datetime | None | MissingType,
    badge_tag: PromotionBadgeTag | None | MissingType,
    display_priority: int | None | MissingType,
    discount_percent_value: int | None | MissingType,
    discount_amount_eur: Decimal | None | MissingType,
) -> None:
    if not any(
        (
            is_enabled is not Missing,
            starts_at is not Missing,
            ends_at is not Missing,
            badge_tag is not Missing,
            display_priority is not Missing,
            discount_percent_value is not Missing,
            discount_amount_eur is not Missing,
        )
    ):
        raise PromotionValidationError(
            "At least one field must be provided for promotion update."
        )

    if is_enabled is not Missing:
        if is_enabled is None:
            raise PromotionValidationError("Promotion is_enabled is required.")
        promotion.is_enabled = is_enabled

    if starts_at is not Missing:
        promotion.starts_at = starts_at

    if ends_at is not Missing:
        promotion.ends_at = ends_at

    if badge_tag is not Missing:
        promotion.badge_tag = badge_tag

    if display_priority is not Missing:
        if display_priority is None:
            raise PromotionValidationError(
                "Promotion display_priority is required."
            )
        _validate_display_priority(display_priority=display_priority)
        promotion.display_priority = display_priority

    if discount_percent_value is not Missing:
        if promotion.discount_type is not PromotionDiscountType.PERCENT:
            raise PromotionValidationError(
                "discount_percent_value can be changed only for PERCENT promotions."
            )
        if discount_percent_value is None:
            raise PromotionValidationError(
                "Promotion discount_percent_value is required."
            )
        promotion.discount_percent_value = discount_percent_value

    if discount_amount_eur is not Missing:
        if promotion.discount_type is not PromotionDiscountType.FIXED_AMOUNT:
            raise PromotionValidationError(
                "discount_amount_eur can be changed only for FIXED_AMOUNT promotions."
            )
        if discount_amount_eur is None:
            raise PromotionValidationError(
                "Promotion discount_amount_eur is required."
            )
        promotion.discount_amount_eur = discount_amount_eur

    _validate_promotion_state(
        audience=promotion.audience,
        category_id=promotion.category_id,
        discount_type=promotion.discount_type,
        discount_percent_value=promotion.discount_percent_value,
        discount_amount_eur=promotion.discount_amount_eur,
        badge_tag=promotion.badge_tag,
        starts_at=promotion.starts_at,
        ends_at=promotion.ends_at,
    )


async def get_lot_for_promotion(
    *,
    lot_id: int,
) -> ServiceLot:
    query = select(ServiceLot).where(ServiceLot.id == lot_id).limit(1)
    result = await s.db.execute(query)
    lot = result.scalar_one_or_none()
    if lot is None:
        raise PromotionLotNotFoundError("Lot not found.")
    return lot


async def get_category_for_promotion(
    *,
    category_id: int,
) -> ServiceCategory:
    query = select(ServiceCategory).where(ServiceCategory.id == category_id).limit(
        1
    )
    result = await s.db.execute(query)
    category = result.scalar_one_or_none()
    if category is None:
        raise PromotionCategoryNotFoundError("Category not found.")
    return category


async def get_target_user_for_promotion(
    *,
    user_id: int,
) -> User:
    query = select(User).where(User.id == user_id).limit(1)
    result = await s.db.execute(query)
    user = result.scalar_one_or_none()
    if user is None:
        raise PromotionTargetUserNotFoundError("User not found.")
    return user


def create_promotion_bl(
    *,
    audience: PromotionAudience,
    lot: ServiceLot | None,
    category: ServiceCategory | None,
    discount_type: PromotionDiscountType | None,
    discount_percent_value: int | None,
    discount_amount_eur: Decimal | None,
    badge_tag: PromotionBadgeTag | None,
    display_priority: int,
    is_enabled: bool,
    starts_at: datetime | None,
    ends_at: datetime | None,
    target_user: User | None,
    assignment_expires_at: datetime | None,
) -> tuple[Promotion, PersonalPromotionAssignment | None]:
    _validate_scope(lot=lot, category=category)
    _validate_display_priority(display_priority=display_priority)
    _validate_personal_assignment(
        audience=audience,
        discount_type=discount_type,
        target_user=target_user,
        assignment_expires_at=assignment_expires_at,
    )
    _validate_promotion_state(
        audience=audience,
        category_id=category.id if category is not None else None,
        discount_type=discount_type,
        discount_percent_value=discount_percent_value,
        discount_amount_eur=discount_amount_eur,
        badge_tag=badge_tag,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    promotion = Promotion(
        audience=audience,
        lot_id=lot.id if lot is not None else None,
        category_id=category.id if category is not None else None,
        discount_type=discount_type,
        discount_percent_value=discount_percent_value,
        discount_amount_eur=discount_amount_eur,
        badge_tag=badge_tag,
        display_priority=display_priority,
        is_enabled=is_enabled,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    assignment = None
    if target_user is not None:
        assignment = PersonalPromotionAssignment(
            promotion=promotion,
            user_id=target_user.id,
            is_one_time=True,
            expires_at=assignment_expires_at,
        )

    return promotion, assignment


async def create_promotion(
    *,
    audience: PromotionAudience,
    lot: ServiceLot | None,
    category: ServiceCategory | None,
    discount_type: PromotionDiscountType | None,
    discount_percent_value: int | None,
    discount_amount_eur: Decimal | None,
    badge_tag: PromotionBadgeTag | None,
    display_priority: int,
    is_enabled: bool,
    starts_at: datetime | None,
    ends_at: datetime | None,
    target_user: User | None,
    assignment_expires_at: datetime | None,
) -> Promotion:
    await _validate_public_scope_uniqueness(
        audience=audience,
        lot=lot,
        category=category,
    )

    promotion, assignment = create_promotion_bl(
        audience=audience,
        lot=lot,
        category=category,
        discount_type=discount_type,
        discount_percent_value=discount_percent_value,
        discount_amount_eur=discount_amount_eur,
        badge_tag=badge_tag,
        display_priority=display_priority,
        is_enabled=is_enabled,
        starts_at=starts_at,
        ends_at=ends_at,
        target_user=target_user,
        assignment_expires_at=assignment_expires_at,
    )

    s.db.add(promotion)
    if assignment is not None:
        s.db.add(assignment)

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_public_lot_scope_conflict(exc):
            raise PromotionValidationError(
                "Public promotion for this lot already exists."
            ) from exc
        if _is_public_category_scope_conflict(exc):
            raise PromotionValidationError(
                "Public promotion for this category already exists."
            ) from exc
        raise PromotionValidationError(
            "Cannot create promotion with provided data."
        ) from exc

    return promotion
