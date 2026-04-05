from __future__ import annotations

from datetime import datetime, timezone
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from wow_shop.infrastructure.db.session import s
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    LotNotFoundError,
    LotOptionAlreadyExistsError,
    LotOptionNotFoundError,
    LotOptionValueAlreadyExistsError,
    LotOptionValueNotFoundError,
    LotPageBlockNotFoundError,
    LotPageNotFoundError,
)
from wow_shop.modules.catalog.application.read_utils import (
    apply_public_lot_visibility,
)
from wow_shop.modules.catalog.constants import (
    CATEGORY_SLUG_PATTERN,
    GAME_SLUG_PATTERN,
    LOT_OPTION_CODE_PATTERN,
    LOT_OPTION_SCOPE_CODE_CONSTRAINTS,
    LOT_OPTION_VALUE_CODE_PATTERN,
    LOT_OPTION_VALUE_SCOPE_CODE_CONSTRAINTS,
    LOT_SLUG_PATTERN,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    LotOption,
    LotOptionInputType,
    LotOptionValue,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServiceLotStatus,
    ServicePage,
    ServicePageBlock,
    ServicePageStatus,
)
from wow_shop.shared.utils.missing import Missing, MissingType


def _normalize_required_text(value: str, *, field_label: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise CatalogValidationError(f"{field_label} is required.")
    return normalized_value


def _normalize_lot_name(name: str) -> str:
    return _normalize_required_text(name, field_label="Lot name")


def _normalize_lot_slug(slug: str) -> str:
    normalized_slug = _normalize_required_text(
        slug,
        field_label="Lot slug",
    ).lower()
    if not LOT_SLUG_PATTERN.fullmatch(normalized_slug):
        raise CatalogValidationError(
            "Lot slug must contain lowercase letters, digits, "
            "hyphens, or underscores."
        )
    return normalized_slug


def _normalize_game_slug(slug: str) -> str:
    normalized_slug = _normalize_required_text(
        slug,
        field_label="Game slug",
    ).lower()
    if not GAME_SLUG_PATTERN.fullmatch(normalized_slug):
        raise CatalogValidationError(
            "Game slug must contain lowercase letters, digits, "
            "hyphens, or underscores."
        )
    return normalized_slug


def _normalize_category_slug(slug: str) -> str:
    normalized_slug = _normalize_required_text(
        slug,
        field_label="Category slug",
    ).lower()
    if not CATEGORY_SLUG_PATTERN.fullmatch(normalized_slug):
        raise CatalogValidationError(
            "Category slug must contain lowercase letters, digits, "
            "hyphens, or underscores."
        )
    return normalized_slug


def _normalize_option_label(label: str) -> str:
    return _normalize_required_text(label, field_label="Option label")


def _normalize_option_code(code: str) -> str:
    normalized_code = _normalize_required_text(
        code,
        field_label="Option code",
    ).lower()
    if not LOT_OPTION_CODE_PATTERN.fullmatch(normalized_code):
        raise CatalogValidationError(
            "Option code must contain lowercase letters, digits, "
            "hyphens, or underscores."
        )
    return normalized_code


def _normalize_option_value_label(label: str) -> str:
    return _normalize_required_text(label, field_label="Option value label")


def _normalize_option_value_code(code: str) -> str:
    normalized_code = _normalize_required_text(
        code,
        field_label="Option value code",
    ).lower()
    if not LOT_OPTION_VALUE_CODE_PATTERN.fullmatch(normalized_code):
        raise CatalogValidationError(
            "Option value code must contain lowercase letters, digits, "
            "hyphens, or underscores."
        )
    return normalized_code


def _validate_positive_id(value: int, *, field_label: str) -> None:
    if value <= 0:
        raise CatalogValidationError(
            f"{field_label} must be a positive integer."
        )


def _validate_optional_positive_id(
    value: int | None,
    *,
    field_label: str,
) -> None:
    if value is not None and value <= 0:
        raise CatalogValidationError(
            f"{field_label} must be a positive integer."
        )


def _validate_non_negative_number(
    value: float,
    *,
    field_label: str,
) -> None:
    if value < 0:
        raise CatalogValidationError(f"{field_label} must be non-negative.")


def _normalize_page_title(title: str | None) -> str | None:
    if title is None:
        return None
    normalized_title = title.strip()
    return normalized_title or None


def _normalize_page_block_type(block_type: str) -> str:
    return _normalize_required_text(
        block_type,
        field_label="Page block type",
    ).lower()


def _normalize_position(
    position: int | None,
    *,
    field_label: str,
) -> int | None:
    if position is None:
        return None
    if position < 0:
        raise CatalogValidationError(f"{field_label} must be non-negative.")
    return position


def _is_unique_violation(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    return sqlstate == "23505"


def _is_foreign_key_violation(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    return sqlstate == "23503"


def _extract_constraint_name(exc: IntegrityError) -> str | None:
    original_error = exc.orig
    constraint_name = getattr(original_error, "constraint_name", None)
    if constraint_name is None:
        diag = getattr(original_error, "diag", None)
        constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name is not None:
        return constraint_name

    original_message = str(original_error)
    if not original_message:
        return None
    return original_message


def _is_option_scope_code_conflict(exc: IntegrityError) -> bool:
    if not _is_unique_violation(exc):
        return False
    constraint_or_message = _extract_constraint_name(exc)
    if constraint_or_message is None:
        return False
    return any(
        constraint in constraint_or_message
        for constraint in LOT_OPTION_SCOPE_CODE_CONSTRAINTS
    )


def _is_option_value_scope_code_conflict(exc: IntegrityError) -> bool:
    if not _is_unique_violation(exc):
        return False
    constraint_or_message = _extract_constraint_name(exc)
    if constraint_or_message is None:
        return False
    return any(
        constraint in constraint_or_message
        for constraint in LOT_OPTION_VALUE_SCOPE_CODE_CONSTRAINTS
    )


async def _get_category_by_id(category_id: int) -> ServiceCategory | None:
    query = select(ServiceCategory).where(ServiceCategory.id == category_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _category_has_children(category_id: int) -> bool:
    query = (
        select(ServiceCategory.id)
        .where(ServiceCategory.parent_id == category_id)
        .limit(1)
    )
    result = await s.db.execute(query)
    return result.scalar_one_or_none() is not None


async def _get_lot_by_id(lot_id: int) -> ServiceLot | None:
    query = select(ServiceLot).where(ServiceLot.id == lot_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _get_lot_detail_by_id(lot_id: int) -> ServiceLot | None:
    query = (
        select(ServiceLot)
        .options(
            joinedload(ServiceLot.category),
            selectinload(ServiceLot.options).selectinload(LotOption.values),
            joinedload(ServiceLot.page).selectinload(ServicePage.blocks),
        )
        .where(ServiceLot.id == lot_id)
    )
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _get_lot_page_by_lot_id(
    lot_id: int,
    *,
    with_blocks: bool,
) -> ServicePage | None:
    query = select(ServicePage).where(ServicePage.lot_id == lot_id)
    if with_blocks:
        query = query.options(selectinload(ServicePage.blocks))
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _get_lot_page_or_raise(
    lot_id: int,
    *,
    with_blocks: bool = True,
) -> ServicePage:
    page = await _get_lot_page_by_lot_id(lot_id, with_blocks=with_blocks)
    if page is None:
        raise LotPageNotFoundError("Lot page not found.")
    return page


async def _get_lot_option_by_id(
    *,
    lot_id: int,
    option_id: int,
    with_values: bool,
) -> LotOption | None:
    query = select(LotOption).where(
        LotOption.id == option_id,
        LotOption.lot_id == lot_id,
    )
    if with_values:
        query = query.options(selectinload(LotOption.values))
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _get_lot_option_or_raise(
    *,
    lot_id: int,
    option_id: int,
    with_values: bool = True,
) -> LotOption:
    option = await _get_lot_option_by_id(
        lot_id=lot_id,
        option_id=option_id,
        with_values=with_values,
    )
    if option is None:
        raise LotOptionNotFoundError("Lot option not found.")
    return option


async def _get_option_value_by_id(
    *,
    option_id: int,
    value_id: int,
) -> LotOptionValue | None:
    query = select(LotOptionValue).where(
        LotOptionValue.id == value_id,
        LotOptionValue.option_id == option_id,
    )
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _get_option_value_or_raise(
    *,
    option_id: int,
    value_id: int,
) -> LotOptionValue:
    value = await _get_option_value_by_id(
        option_id=option_id,
        value_id=value_id,
    )
    if value is None:
        raise LotOptionValueNotFoundError("Lot option value not found.")
    return value


async def _lot_slug_exists_in_scope(
    *,
    category_id: int,
    slug: str,
    exclude_lot_id: int | None = None,
) -> bool:
    query = (
        select(ServiceLot.id)
        .where(
            ServiceLot.category_id == category_id,
            ServiceLot.slug == slug,
        )
        .limit(1)
    )
    if exclude_lot_id is not None:
        query = query.where(ServiceLot.id != exclude_lot_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none() is not None


async def _lot_option_code_exists_in_scope(
    *,
    lot_id: int,
    code: str,
    exclude_option_id: int | None = None,
) -> bool:
    query = select(LotOption.id).where(
        LotOption.lot_id == lot_id,
        LotOption.code == code,
    )
    if exclude_option_id is not None:
        query = query.where(LotOption.id != exclude_option_id)
    result = await s.db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def _lot_option_value_code_exists_in_scope(
    *,
    option_id: int,
    code: str,
    exclude_value_id: int | None = None,
) -> bool:
    query = select(LotOptionValue.id).where(
        LotOptionValue.option_id == option_id,
        LotOptionValue.code == code,
    )
    if exclude_value_id is not None:
        query = query.where(LotOptionValue.id != exclude_value_id)
    result = await s.db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def _resolve_lot_option_dependencies(
    *,
    lot_id: int,
    depends_on_option_id: int | None,
    depends_on_value_id: int | None,
    current_option_id: int | None = None,
) -> tuple[int | None, int | None]:
    if depends_on_option_id is None and depends_on_value_id is None:
        return None, None

    if depends_on_option_id is None or depends_on_value_id is None:
        raise CatalogValidationError(
            "Both depends_on_option_id and depends_on_value_id must be set "
            "together."
        )

    dependency_option = await _get_lot_option_by_id(
        lot_id=lot_id,
        option_id=depends_on_option_id,
        with_values=False,
    )
    if dependency_option is None:
        raise LotOptionNotFoundError("Dependency option not found.")

    if current_option_id is not None and dependency_option.id == current_option_id:
        raise CatalogValidationError("Option cannot depend on itself.")

    dependency_value = await _get_option_value_by_id(
        option_id=dependency_option.id,
        value_id=depends_on_value_id,
    )
    if dependency_value is None:
        raise LotOptionValueNotFoundError("Dependency option value not found.")

    return dependency_option.id, dependency_value.id


def _ordered_page_blocks(page: ServicePage) -> list[ServicePageBlock]:
    return sorted(page.blocks, key=lambda block: (block.position, block.id))


def _normalize_insert_index(position: int | None, *, items_count: int) -> int:
    if position is None:
        return items_count
    return min(position, items_count)


async def _reindex_page_blocks(
    blocks: list[ServicePageBlock],
) -> None:
    if not blocks:
        return

    for index, block in enumerate(blocks, start=1):
        block.position = -index
    await s.db.flush()

    for index, block in enumerate(blocks):
        block.position = index
    await s.db.flush()


def _mark_page_as_draft(page: ServicePage) -> None:
    page.status = ServicePageStatus.DRAFT
    page.published_at = None


def _validate_lot_status_transition(
    *,
    current_status: ServiceLotStatus,
    target_status: ServiceLotStatus,
    via_soft_delete: bool = False,
) -> None:
    if current_status == target_status:
        return

    if via_soft_delete:
        allowed_transitions = {
            ServiceLotStatus.DRAFT: {ServiceLotStatus.DELETED},
            ServiceLotStatus.ACTIVE: {ServiceLotStatus.DELETED},
            ServiceLotStatus.INACTIVE: {ServiceLotStatus.DELETED},
            ServiceLotStatus.DELETED: {ServiceLotStatus.DELETED},
        }
        via_label = "soft delete"
    else:
        allowed_transitions = {
            ServiceLotStatus.DRAFT: {
                ServiceLotStatus.ACTIVE,
                ServiceLotStatus.INACTIVE,
            },
            ServiceLotStatus.ACTIVE: {ServiceLotStatus.INACTIVE},
            ServiceLotStatus.INACTIVE: {ServiceLotStatus.ACTIVE},
            ServiceLotStatus.DELETED: {ServiceLotStatus.INACTIVE},
        }
        via_label = "patch"

    allowed_targets = allowed_transitions.get(current_status, set())
    if target_status not in allowed_targets:
        raise CatalogValidationError(
            "Lot status transition from "
            f"{current_status.name} to {target_status.name} "
            f"is not allowed via {via_label}."
        )


async def _run_lot_soft_delete_prechecks(*, lot: ServiceLot) -> None:
    # Reserved for future business pre-checks (orders/relations constraints).
    _ = lot


def create_lot_bl(
    *,
    category: ServiceCategory,
    name: str,
    slug: str,
    description: str | None,
    status: ServiceLotStatus,
    base_price_eur: float,
) -> ServiceLot:
    normalized_name = _normalize_lot_name(name)
    normalized_slug = _normalize_lot_slug(slug)
    _validate_non_negative_number(base_price_eur, field_label="Base price EUR")
    if status == ServiceLotStatus.DELETED:
        raise CatalogValidationError(
            "Lot cannot be created with DELETED status."
        )

    return ServiceLot(
        category_id=category.id,
        name=normalized_name,
        slug=normalized_slug,
        description=description,
        status=status,
        base_price_eur=base_price_eur,
    )


class LotEditScope(NamedTuple):
    category_id: int
    slug: str
    should_check_slug_scope: bool


class LotOptionEditScope(NamedTuple):
    code: str
    should_check_code_scope: bool


class LotOptionValueEditScope(NamedTuple):
    code: str
    should_check_code_scope: bool


def edit_lot_bl(
    *,
    lot: ServiceLot,
    category: ServiceCategory | MissingType,
    name: str | MissingType,
    slug: str | MissingType,
    description: str | None | MissingType,
    status: ServiceLotStatus | MissingType,
    base_price_eur: float | MissingType,
) -> LotEditScope:
    if not any(
        (
            category is not Missing,
            name is not Missing,
            slug is not Missing,
            description is not Missing,
            status is not Missing,
            base_price_eur is not Missing,
        )
    ):
        raise CatalogValidationError(
            "At least one field must be provided for lot update."
        )

    target_category_id = lot.category_id
    target_slug = lot.slug
    should_check_slug_scope = False

    if category is not Missing:
        lot.category_id = category.id
        target_category_id = category.id
        should_check_slug_scope = True

    if name is not Missing:
        lot.name = _normalize_lot_name(name)

    if slug is not Missing:
        target_slug = _normalize_lot_slug(slug)
        lot.slug = target_slug
        should_check_slug_scope = True

    if description is not Missing:
        lot.description = description

    if status is not Missing:
        _validate_lot_status_transition(
            current_status=lot.status,
            target_status=status,
            via_soft_delete=False,
        )
        lot.status = status

    if base_price_eur is not Missing:
        _validate_non_negative_number(
            base_price_eur,
            field_label="Base price EUR",
        )
        lot.base_price_eur = base_price_eur

    if lot.status == ServiceLotStatus.DELETED:
        if lot.deleted_at is None:
            lot.deleted_at = datetime.now(timezone.utc)
    else:
        lot.deleted_at = None

    return LotEditScope(
        category_id=target_category_id,
        slug=target_slug,
        should_check_slug_scope=should_check_slug_scope,
    )


def edit_lot_option_bl(
    *,
    option: LotOption,
    label: str | MissingType,
    code: str | MissingType,
    input_type: LotOptionInputType | MissingType,
    is_required: bool | MissingType,
    is_active: bool | MissingType,
    depends_on_option_id: int | None | MissingType,
    depends_on_value_id: int | None | MissingType,
) -> LotOptionEditScope:
    update_dependencies = (
        depends_on_option_id is not Missing
        or depends_on_value_id is not Missing
    )
    if not any(
        (
            label is not Missing,
            code is not Missing,
            input_type is not Missing,
            is_required is not Missing,
            is_active is not Missing,
            update_dependencies,
        )
    ):
        raise CatalogValidationError(
            "At least one field must be provided for option update."
        )

    target_code = option.code
    should_check_code_scope = False

    if label is not Missing:
        option.label = _normalize_option_label(label)

    if code is not Missing:
        target_code = _normalize_option_code(code)
        option.code = target_code
        should_check_code_scope = True

    if input_type is not Missing:
        option.input_type = input_type

    if is_required is not Missing:
        option.is_required = is_required

    if is_active is not Missing:
        option.is_active = is_active

    if update_dependencies:
        if (
            depends_on_option_id is Missing
            or depends_on_value_id is Missing
        ):
            raise CatalogValidationError(
                "Both depends_on_option_id and depends_on_value_id must be set "
                "together."
            )
        option.depends_on_option_id = depends_on_option_id
        option.depends_on_value_id = depends_on_value_id

    return LotOptionEditScope(
        code=target_code,
        should_check_code_scope=should_check_code_scope,
    )


def edit_lot_option_value_bl(
    *,
    value: LotOptionValue,
    label: str | MissingType,
    code: str | MissingType,
    description: str | None | MissingType,
    price_value: float | MissingType,
    is_default: bool | MissingType,
    is_active: bool | MissingType,
) -> LotOptionValueEditScope:
    if not any(
        (
            label is not Missing,
            code is not Missing,
            description is not Missing,
            price_value is not Missing,
            is_default is not Missing,
            is_active is not Missing,
        )
    ):
        raise CatalogValidationError(
            "At least one field must be provided for option value update."
        )

    target_code = value.code
    should_check_code_scope = False

    if label is not Missing:
        value.label = _normalize_option_value_label(label)

    if code is not Missing:
        target_code = _normalize_option_value_code(code)
        value.code = target_code
        should_check_code_scope = True

    if description is not Missing:
        value.description = description

    if price_value is not Missing:
        _validate_non_negative_number(
            price_value,
            field_label="Option value price",
        )
        value.price_value = price_value

    if is_default is not Missing:
        value.is_default = is_default

    if is_active is not Missing:
        value.is_active = is_active

    return LotOptionValueEditScope(
        code=target_code,
        should_check_code_scope=should_check_code_scope,
    )


def edit_lot_page_block_bl(
    *,
    block: ServicePageBlock,
    payload_json: dict | None | MissingType,
) -> None:
    if payload_json is Missing:
        raise CatalogValidationError(
            "At least one field must be provided for page block update."
        )

    block.payload_json = payload_json


async def soft_delete_lot(
    *,
    lot_id: int,
) -> ServiceLot:
    _validate_positive_id(lot_id, field_label="Lot id")

    lot = await _get_lot_by_id(lot_id)
    if lot is None:
        raise LotNotFoundError("Lot not found.")

    await _run_lot_soft_delete_prechecks(lot=lot)
    _validate_lot_status_transition(
        current_status=lot.status,
        target_status=ServiceLotStatus.DELETED,
        via_soft_delete=True,
    )

    update_required = False
    if lot.status != ServiceLotStatus.DELETED:
        lot.status = ServiceLotStatus.DELETED
        update_required = True
    if lot.deleted_at is None:
        lot.deleted_at = datetime.now(timezone.utc)
        update_required = True

    if update_required:
        await s.db.flush()

    deleted_lot = await _get_lot_detail_by_id(lot.id)
    if deleted_lot is None:
        raise LotNotFoundError("Lot not found.")
    return deleted_lot


async def restore_lot(
    *,
    lot_id: int,
) -> ServiceLot:
    _validate_positive_id(lot_id, field_label="Lot id")

    lot = await _get_lot_by_id(lot_id)
    if lot is None:
        raise LotNotFoundError("Lot not found.")
    if lot.status != ServiceLotStatus.DELETED:
        raise CatalogValidationError(
            "Lot restore is allowed only from DELETED status."
        )

    lot.status = ServiceLotStatus.INACTIVE
    lot.deleted_at = None
    await s.db.flush()

    restored_lot = await _get_lot_detail_by_id(lot.id)
    if restored_lot is None:
        raise LotNotFoundError("Lot not found.")
    return restored_lot


async def list_lots(
    *,
    game_id: int | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
) -> list[ServiceLot]:
    _validate_optional_positive_id(game_id, field_label="Game id")
    _validate_optional_positive_id(category_id, field_label="Category id")

    query = (
        select(ServiceLot)
        .join(ServiceLot.category)
        .options(joinedload(ServiceLot.category))
    )
    if game_id is not None:
        query = query.where(ServiceCategory.game_id == game_id)
    if category_id is not None:
        query = query.where(ServiceLot.category_id == category_id)
    if not include_inactive:
        query = query.where(
            ServiceLot.status == ServiceLotStatus.ACTIVE,
            ServiceCategory.status == ServiceCategoryStatus.ACTIVE,
            Game.status == GameStatus.ACTIVE,
            ServicePage.status == ServicePageStatus.PUBLISHED,
        ).join(ServiceCategory.game).join(ServiceLot.page)

    query = query.order_by(
        ServiceCategory.sort_order.asc(),
        ServiceCategory.id.asc(),
        ServiceLot.id.asc(),
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())


async def get_public_lot_by_slugs(
    *,
    game_slug: str,
    category_slug: str,
    lot_slug: str,
) -> ServiceLot:
    normalized_game_slug = _normalize_game_slug(game_slug)
    normalized_category_slug = _normalize_category_slug(category_slug)
    normalized_lot_slug = _normalize_lot_slug(lot_slug)

    query = (
        select(ServiceLot)
        .join(ServiceLot.category)
        .join(ServiceCategory.game)
        .join(ServiceLot.page)
        .options(
            joinedload(ServiceLot.category),
            selectinload(ServiceLot.options).selectinload(LotOption.values),
            joinedload(ServiceLot.page).selectinload(ServicePage.blocks),
        )
        .where(
            Game.slug == normalized_game_slug,
            ServiceCategory.slug == normalized_category_slug,
            ServiceLot.slug == normalized_lot_slug,
        )
    )
    query = apply_public_lot_visibility(query)

    result = await s.db.execute(query)
    lots = list(result.scalars().all())
    if not lots:
        raise LotNotFoundError("Lot not found.")
    if len(lots) > 1:
        raise CatalogValidationError(
            "Lot slug is ambiguous in game/category scope."
        )
    return lots[0]


async def get_staff_lot_by_slugs(
    *,
    game_slug: str,
    category_slug: str,
    lot_slug: str,
) -> ServiceLot:
    normalized_game_slug = _normalize_game_slug(game_slug)
    normalized_category_slug = _normalize_category_slug(category_slug)
    normalized_lot_slug = _normalize_lot_slug(lot_slug)

    query = (
        select(ServiceLot)
        .join(ServiceLot.category)
        .join(ServiceCategory.game)
        .options(
            joinedload(ServiceLot.category),
            selectinload(ServiceLot.options).selectinload(LotOption.values),
            joinedload(ServiceLot.page).selectinload(ServicePage.blocks),
        )
        .where(
            Game.slug == normalized_game_slug,
            ServiceCategory.slug == normalized_category_slug,
            ServiceLot.slug == normalized_lot_slug,
        )
    )

    result = await s.db.execute(query)
    lots = list(result.scalars().all())
    if not lots:
        raise LotNotFoundError("Lot not found.")
    if len(lots) > 1:
        raise CatalogValidationError(
            "Lot slug is ambiguous in game/category scope."
        )
    return lots[0]


async def upsert_lot_page(
    *,
    lot_id: int,
    title: str | None,
    meta_json: dict | None,
) -> ServicePage:
    _validate_positive_id(lot_id, field_label="Lot id")

    lot = await _get_lot_by_id(lot_id)
    if lot is None:
        raise LotNotFoundError("Lot not found.")

    normalized_title = _normalize_page_title(title)
    page = await _get_lot_page_by_lot_id(lot_id, with_blocks=True)
    if page is None:
        page = ServicePage(
            lot_id=lot.id,
            status=ServicePageStatus.DRAFT,
            title=normalized_title,
            meta_json=meta_json,
            published_at=None,
        )
        s.db.add(page)
        await s.db.flush()
        return await _get_lot_page_or_raise(lot_id)

    page.title = normalized_title
    page.meta_json = meta_json
    _mark_page_as_draft(page)
    await s.db.flush()
    return await _get_lot_page_or_raise(lot_id)


async def get_lot_page(
    *,
    lot_id: int,
) -> ServicePage:
    _validate_positive_id(lot_id, field_label="Lot id")
    return await _get_lot_page_or_raise(lot_id)


async def change_lot_page_status(
    *,
    lot_id: int,
    status: ServicePageStatus,
) -> ServicePage:
    _validate_positive_id(lot_id, field_label="Lot id")

    page = await _get_lot_page_or_raise(lot_id)
    if page.status == status:
        return page

    if status == ServicePageStatus.PUBLISHED:
        page.status = ServicePageStatus.PUBLISHED
        page.published_at = datetime.now(timezone.utc)
    else:
        page.status = ServicePageStatus.DRAFT
        page.published_at = None

    await s.db.flush()
    return await _get_lot_page_or_raise(lot_id)


async def create_lot_page_block(
    *,
    lot_id: int,
    block_type: str,
    payload_json: dict | None,
    position: int | None,
) -> ServicePage:
    _validate_positive_id(lot_id, field_label="Lot id")
    normalized_type = _normalize_page_block_type(block_type)
    normalized_position = _normalize_position(
        position,
        field_label="Block position",
    )

    page = await _get_lot_page_or_raise(lot_id)
    ordered_blocks = _ordered_page_blocks(page)
    insert_index = _normalize_insert_index(
        normalized_position,
        items_count=len(ordered_blocks),
    )

    new_block = ServicePageBlock(
        page_id=page.id,
        position=0,
        type=normalized_type,
        payload_json=payload_json,
    )
    s.db.add(new_block)
    await s.db.flush()

    ordered_blocks.insert(insert_index, new_block)
    await _reindex_page_blocks(ordered_blocks)
    _mark_page_as_draft(page)
    await s.db.flush()
    return await _get_lot_page_or_raise(lot_id)


async def delete_lot_page_block(
    *,
    lot_id: int,
    block_id: int,
) -> ServicePage:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(block_id, field_label="Block id")

    page = await _get_lot_page_or_raise(lot_id)
    block = next((item for item in page.blocks if item.id == block_id), None)
    if block is None:
        raise LotPageBlockNotFoundError("Lot page block not found.")

    ordered_remaining_blocks = [
        item for item in _ordered_page_blocks(page) if item.id != block.id
    ]
    await s.db.delete(block)
    await s.db.flush()
    await _reindex_page_blocks(ordered_remaining_blocks)

    _mark_page_as_draft(page)
    await s.db.flush()
    return await _get_lot_page_or_raise(lot_id)


async def list_lot_options(
    *,
    lot_id: int,
    include_inactive: bool = True,
) -> list[LotOption]:
    _validate_positive_id(lot_id, field_label="Lot id")

    lot = await _get_lot_by_id(lot_id)
    if lot is None:
        raise LotNotFoundError("Lot not found.")

    query = (
        select(LotOption)
        .options(selectinload(LotOption.values))
        .where(LotOption.lot_id == lot.id)
    )
    if not include_inactive:
        query = query.where(LotOption.is_active.is_(True))

    query = query.order_by(
        LotOption.sort_order.asc(),
        LotOption.id.asc(),
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())


async def get_lot_option(
    *,
    lot_id: int,
    option_id: int,
) -> LotOption:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(option_id, field_label="Option id")
    return await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option_id,
        with_values=True,
    )


async def create_lot_option(
    *,
    lot_id: int,
    label: str,
    code: str,
    input_type: LotOptionInputType,
    is_required: bool,
    sort_order: int,
    is_active: bool,
    depends_on_option_id: int | None,
    depends_on_value_id: int | None,
) -> LotOption:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_non_negative_number(
        float(sort_order),
        field_label="Option sort order",
    )
    _validate_optional_positive_id(
        depends_on_option_id,
        field_label="depends_on_option_id",
    )
    _validate_optional_positive_id(
        depends_on_value_id,
        field_label="depends_on_value_id",
    )

    lot = await _get_lot_by_id(lot_id)
    if lot is None:
        raise LotNotFoundError("Lot not found.")

    normalized_label = _normalize_option_label(label)
    normalized_code = _normalize_option_code(code)
    dependency_option_id, dependency_value_id = (
        await _resolve_lot_option_dependencies(
            lot_id=lot.id,
            depends_on_option_id=depends_on_option_id,
            depends_on_value_id=depends_on_value_id,
        )
    )

    if await _lot_option_code_exists_in_scope(
        lot_id=lot.id,
        code=normalized_code,
    ):
        raise LotOptionAlreadyExistsError(
            "Lot option with this code already exists in this lot."
        )

    option = LotOption(
        lot_id=lot.id,
        label=normalized_label,
        code=normalized_code,
        input_type=input_type,
        is_required=is_required,
        sort_order=sort_order,
        is_active=is_active,
        depends_on_option_id=dependency_option_id,
        depends_on_value_id=dependency_value_id,
    )
    s.db.add(option)
    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_option_scope_code_conflict(exc):
            raise LotOptionAlreadyExistsError(
                "Lot option with this code already exists in this lot."
            ) from exc
        if _is_foreign_key_violation(exc):
            raise CatalogValidationError(
                "Invalid option dependency."
            ) from exc
        raise

    return await _get_lot_option_or_raise(
        lot_id=lot.id,
        option_id=option.id,
        with_values=True,
    )


async def delete_lot_option(
    *,
    lot_id: int,
    option_id: int,
) -> list[LotOption]:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(option_id, field_label="Option id")

    option = await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option_id,
        with_values=True,
    )
    await s.db.delete(option)
    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_foreign_key_violation(exc):
            raise CatalogValidationError(
                "Option is used in dependencies and cannot be deleted."
            ) from exc
        raise

    return await list_lot_options(lot_id=lot_id, include_inactive=True)


async def create_lot_option_value(
    *,
    lot_id: int,
    option_id: int,
    label: str,
    code: str,
    description: str | None,
    price_value: float,
    sort_order: int,
    is_default: bool,
    is_active: bool,
) -> LotOption:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(option_id, field_label="Option id")
    _validate_non_negative_number(
        price_value,
        field_label="Option value price",
    )
    _validate_non_negative_number(
        float(sort_order),
        field_label="Option value sort order",
    )

    option = await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option_id,
        with_values=True,
    )
    normalized_label = _normalize_option_value_label(label)
    normalized_code = _normalize_option_value_code(code)

    if await _lot_option_value_code_exists_in_scope(
        option_id=option.id,
        code=normalized_code,
    ):
        raise LotOptionValueAlreadyExistsError(
            "Option value with this code already exists in this option."
        )

    value = LotOptionValue(
        option_id=option.id,
        label=normalized_label,
        code=normalized_code,
        description=description,
        price_value=price_value,
        sort_order=sort_order,
        is_default=is_default,
        is_active=is_active,
    )
    s.db.add(value)
    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_option_value_scope_code_conflict(exc):
            raise LotOptionValueAlreadyExistsError(
                "Option value with this code already exists in this option."
            ) from exc
        raise

    return await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option.id,
        with_values=True,
    )


async def delete_lot_option_value(
    *,
    lot_id: int,
    option_id: int,
    value_id: int,
) -> LotOption:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(option_id, field_label="Option id")
    _validate_positive_id(value_id, field_label="Value id")

    option = await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option_id,
        with_values=True,
    )
    value = await _get_option_value_or_raise(
        option_id=option.id,
        value_id=value_id,
    )

    await s.db.delete(value)
    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_foreign_key_violation(exc):
            raise CatalogValidationError(
                "Option value is used in dependencies and cannot be deleted."
            ) from exc
        raise

    return await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option.id,
        with_values=True,
    )
