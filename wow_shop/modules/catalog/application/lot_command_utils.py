from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from wow_shop.infrastructure.db.session import s
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    LotOptionNotFoundError,
    LotOptionValueNotFoundError,
    LotPageNotFoundError,
)
from wow_shop.modules.catalog.constants import (
    LOT_OPTION_SCOPE_CODE_CONSTRAINTS,
    LOT_OPTION_VALUE_SCOPE_CODE_CONSTRAINTS,
    LOT_SCOPE_SLUG_CONSTRAINTS,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    LotOption,
    LotOptionValue,
    ServiceCategory,
    ServiceLot,
    ServicePage,
    ServicePageBlock,
    ServicePageStatus,
)


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


def _is_lot_scope_slug_conflict(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    if sqlstate != "23505":
        return False

    constraint_name = getattr(original_error, "constraint_name", None)
    if constraint_name is None:
        diag = getattr(original_error, "diag", None)
        constraint_name = getattr(diag, "constraint_name", None)

    if constraint_name in LOT_SCOPE_SLUG_CONSTRAINTS:
        return True

    original_message = str(original_error)
    return any(
        constraint in original_message for constraint in LOT_SCOPE_SLUG_CONSTRAINTS
    )


def _is_option_scope_code_conflict(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    if sqlstate != "23505":
        return False

    constraint_or_message = _extract_constraint_name(exc)
    if constraint_or_message is None:
        return False
    return any(
        constraint in constraint_or_message
        for constraint in LOT_OPTION_SCOPE_CODE_CONSTRAINTS
    )


def _is_option_value_scope_code_conflict(exc: IntegrityError) -> bool:
    original_error = exc.orig
    sqlstate = (
        getattr(original_error, "sqlstate", None)
        or getattr(original_error, "pgcode", None)
    )
    if sqlstate != "23505":
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


async def _list_lot_options_by_lot_id(
    *,
    lot_id: int,
    with_values: bool = True,
) -> list[LotOption]:
    query = select(LotOption).where(LotOption.lot_id == lot_id)
    if with_values:
        query = query.options(selectinload(LotOption.values))
    query = query.order_by(
        LotOption.sort_order.asc(),
        LotOption.id.asc(),
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())


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


def _ordered_page_blocks(page: ServicePage) -> list[ServicePageBlock]:
    return sorted(page.blocks, key=lambda block: (block.position, block.id))


def _normalize_insert_index(position: int | None, *, items_count: int) -> int:
    if position is None:
        return items_count
    return min(position, items_count)


async def _reindex_page_blocks(blocks: list[ServicePageBlock]) -> None:
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


def _validate_full_reorder_ids(
    *,
    scope_ids: list[int],
    requested_ids: list[int],
    entity_label: str,
) -> None:
    if len(requested_ids) != len(set(requested_ids)):
        raise CatalogValidationError(
            f"{entity_label} reorder payload contains duplicate ids."
        )

    if not scope_ids:
        if requested_ids:
            raise CatalogValidationError(
                f"{entity_label} reorder payload must be empty for empty scope."
            )
        return

    if not requested_ids:
        raise CatalogValidationError(
            f"{entity_label} reorder payload must include all ids in scope."
        )

    scope_ids_set = set(scope_ids)
    requested_ids_set = set(requested_ids)
    missing_ids = sorted(scope_ids_set - requested_ids_set)
    unknown_ids = sorted(requested_ids_set - scope_ids_set)
    if missing_ids or unknown_ids:
        details: list[str] = []
        if missing_ids:
            details.append(f"missing ids: {missing_ids}")
        if unknown_ids:
            details.append(f"unknown ids: {unknown_ids}")
        details_message = "; ".join(details)
        raise CatalogValidationError(
            f"Invalid {entity_label} reorder payload ({details_message})."
        )
