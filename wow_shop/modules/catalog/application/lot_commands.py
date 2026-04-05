from __future__ import annotations

from typing import TypeVar

from sqlalchemy.exc import IntegrityError

from wow_shop.modules.catalog.api.request.lot_models import (
    ChangeLotPageStatusRequest,
    CreateLotOptionRequest,
    CreateLotOptionValueRequest,
    CreateLotPageBlockRequest,
    CreateLotRequest,
    PatchLotRequest,
    ReorderLotOptionValuesRequest,
    ReorderLotOptionsRequest,
    ReorderLotPageBlocksRequest,
    UpsertLotPageRequest,
    UpdateLotOptionRequest,
    UpdateLotOptionValueRequest,
    UpdateLotPageBlockRequest,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    CategoryNotFoundError,
    LotAlreadyExistsError,
    LotNotFoundError,
    LotOptionAlreadyExistsError,
    LotOptionNotFoundError,
    LotOptionValueAlreadyExistsError,
    LotOptionValueNotFoundError,
    LotPageBlockNotFoundError,
)
from wow_shop.modules.catalog.application.lot_command_utils import (
    _category_has_children,
    _get_category_by_id,
    _get_lot_by_id,
    _get_lot_detail_by_id,
    _get_lot_option_by_id,
    _get_lot_option_or_raise,
    _get_lot_page_or_raise,
    _list_lot_options_by_lot_id,
    _get_option_value_by_id,
    _get_option_value_or_raise,
    _is_foreign_key_violation,
    _is_lot_scope_slug_conflict,
    _is_option_scope_code_conflict,
    _is_option_value_scope_code_conflict,
    _lot_option_code_exists_in_scope,
    _lot_option_value_code_exists_in_scope,
    _lot_slug_exists_in_scope,
    _mark_page_as_draft,
    _ordered_page_blocks,
    _reindex_page_blocks,
    _validate_full_reorder_ids,
    _validate_optional_positive_id,
    _validate_positive_id,
)
from wow_shop.modules.catalog.application.lot_service import (
    change_lot_page_status as service_change_lot_page_status,
    create_lot_bl,
    create_lot_option as service_create_lot_option,
    create_lot_option_value as service_create_lot_option_value,
    create_lot_page_block as service_create_lot_page_block,
    delete_lot_option as service_delete_lot_option,
    delete_lot_option_value as service_delete_lot_option_value,
    delete_lot_page_block as service_delete_lot_page_block,
    edit_lot_bl,
    edit_lot_option_bl,
    edit_lot_option_value_bl,
    edit_lot_page_block_bl,
    restore_lot as service_restore_lot,
    soft_delete_lot as service_soft_delete_lot,
    upsert_lot_page as service_upsert_lot_page,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    LotOption,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServicePage,
)
from wow_shop.infrastructure.db.session import s
from wow_shop.shared.utils.missing import Missing, MissingType

T = TypeVar("T")


def _resolve_nullable_required_field(
    value: T | None | MissingType,
    *,
    required_error_message: str,
) -> T | MissingType:
    if value is Missing:
        return Missing
    if value is None:
        raise CatalogValidationError(required_error_message)
    return value


async def _resolve_patch_category(
    category_id: int | None | MissingType,
) -> ServiceCategory | MissingType:
    if category_id is Missing:
        return Missing
    if category_id is None:
        raise CatalogValidationError("Lot category_id is required.")
    _validate_positive_id(category_id, field_label="Category id")

    category = await _get_category_by_id(category_id)
    if category is None:
        raise CategoryNotFoundError("Category not found.")
    if await _category_has_children(category.id):
        raise CatalogValidationError(
            "Lot can be assigned only to a leaf category."
        )
    return category


async def _resolve_patch_option_dependencies(
    *,
    lot_id: int,
    current_option_id: int,
    depends_on_option_id: int | None | MissingType,
    depends_on_value_id: int | None | MissingType,
) -> tuple[int | None | MissingType, int | None | MissingType]:
    update_dependencies = (
        depends_on_option_id is not Missing
        or depends_on_value_id is not Missing
    )
    if not update_dependencies:
        return Missing, Missing

    resolved_depends_on_option_id = (
        None
        if depends_on_option_id is Missing
        else depends_on_option_id
    )
    resolved_depends_on_value_id = (
        None
        if depends_on_value_id is Missing
        else depends_on_value_id
    )
    _validate_optional_positive_id(
        resolved_depends_on_option_id,
        field_label="depends_on_option_id",
    )
    _validate_optional_positive_id(
        resolved_depends_on_value_id,
        field_label="depends_on_value_id",
    )

    if (
        resolved_depends_on_option_id is None
        and resolved_depends_on_value_id is None
    ):
        return None, None
    if (
        resolved_depends_on_option_id is None
        or resolved_depends_on_value_id is None
    ):
        raise CatalogValidationError(
            "Both depends_on_option_id and depends_on_value_id must be set "
            "together."
        )

    dependency_option = await _get_lot_option_by_id(
        lot_id=lot_id,
        option_id=resolved_depends_on_option_id,
        with_values=False,
    )
    if dependency_option is None:
        raise LotOptionNotFoundError("Dependency option not found.")
    if dependency_option.id == current_option_id:
        raise CatalogValidationError("Option cannot depend on itself.")

    dependency_value = await _get_option_value_by_id(
        option_id=dependency_option.id,
        value_id=resolved_depends_on_value_id,
    )
    if dependency_value is None:
        raise LotOptionValueNotFoundError("Dependency option value not found.")

    return dependency_option.id, dependency_value.id


async def create_lot(
    *,
    payload: CreateLotRequest,
) -> ServiceLot:
    _validate_positive_id(payload.category_id, field_label="Category id")
    category = await _get_category_by_id(payload.category_id)
    if category is None:
        raise CategoryNotFoundError("Category not found.")
    if category.status != ServiceCategoryStatus.ACTIVE:
        raise CatalogValidationError(
            "Lot can be created only in an active category."
        )
    if await _category_has_children(category.id):
        raise CatalogValidationError(
            "Lot can be created only in a leaf category."
        )

    lot = create_lot_bl(
        category=category,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        status=payload.status,
        base_price_eur=payload.base_price_eur,
    )

    if await _lot_slug_exists_in_scope(
        category_id=category.id,
        slug=lot.slug,
    ):
        raise LotAlreadyExistsError(
            "Lot with this slug already exists in this category."
        )

    s.db.add(lot)
    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_lot_scope_slug_conflict(exc):
            raise LotAlreadyExistsError(
                "Lot with this slug already exists in this category."
            ) from exc
        raise
    return lot


async def patch_lot(
    *,
    lot_id: int,
    payload: PatchLotRequest,
) -> ServiceLot:
    _validate_positive_id(lot_id, field_label="Lot id")

    lot = await _get_lot_by_id(lot_id)
    if lot is None:
        raise LotNotFoundError("Lot not found.")

    category = await _resolve_patch_category(payload.category_id)
    name = _resolve_nullable_required_field(
        payload.name,
        required_error_message="Lot name is required.",
    )
    slug = _resolve_nullable_required_field(
        payload.slug,
        required_error_message="Lot slug is required.",
    )
    status = _resolve_nullable_required_field(
        payload.status,
        required_error_message="Lot status is required.",
    )
    base_price_eur = _resolve_nullable_required_field(
        payload.base_price_eur,
        required_error_message="Lot base_price_eur is required.",
    )

    scope = edit_lot_bl(
        lot=lot,
        category=category,
        name=name,
        slug=slug,
        description=payload.description,
        status=status,
        base_price_eur=base_price_eur,
    )

    if scope.should_check_slug_scope:
        if await _lot_slug_exists_in_scope(
            category_id=scope.category_id,
            slug=scope.slug,
            exclude_lot_id=lot.id,
        ):
            raise LotAlreadyExistsError(
                "Lot with this slug already exists in this category."
            )

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_lot_scope_slug_conflict(exc):
            raise LotAlreadyExistsError(
                "Lot with this slug already exists in this category."
            ) from exc
        raise

    updated_lot = await _get_lot_detail_by_id(lot.id)
    if updated_lot is None:
        raise LotNotFoundError("Lot not found.")
    return updated_lot


async def update_lot_option(
    *,
    lot_id: int,
    option_id: int,
    payload: UpdateLotOptionRequest,
) -> LotOption:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(option_id, field_label="Option id")

    option = await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option_id,
        with_values=True,
    )

    label = _resolve_nullable_required_field(
        payload.label,
        required_error_message="Option label is required.",
    )
    code = _resolve_nullable_required_field(
        payload.code,
        required_error_message="Option code is required.",
    )
    input_type = _resolve_nullable_required_field(
        payload.input_type,
        required_error_message="Option input_type is required.",
    )
    is_required = _resolve_nullable_required_field(
        payload.is_required,
        required_error_message="Option is_required is required.",
    )
    is_active = _resolve_nullable_required_field(
        payload.is_active,
        required_error_message="Option is_active is required.",
    )
    resolved_depends_on_option_id, resolved_depends_on_value_id = (
        await _resolve_patch_option_dependencies(
            lot_id=option.lot_id,
            current_option_id=option.id,
            depends_on_option_id=payload.depends_on_option_id,
            depends_on_value_id=payload.depends_on_value_id,
        )
    )

    scope = edit_lot_option_bl(
        option=option,
        label=label,
        code=code,
        input_type=input_type,
        is_required=is_required,
        is_active=is_active,
        depends_on_option_id=resolved_depends_on_option_id,
        depends_on_value_id=resolved_depends_on_value_id,
    )

    if scope.should_check_code_scope:
        if await _lot_option_code_exists_in_scope(
            lot_id=option.lot_id,
            code=scope.code,
            exclude_option_id=option.id,
        ):
            raise LotOptionAlreadyExistsError(
                "Lot option with this code already exists in this lot."
            )

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
        lot_id=option.lot_id,
        option_id=option.id,
        with_values=True,
    )


async def create_lot_option(
    *,
    lot_id: int,
    payload: CreateLotOptionRequest,
) -> LotOption:
    return await service_create_lot_option(
        lot_id=lot_id,
        label=payload.label,
        code=payload.code,
        input_type=payload.input_type,
        is_required=payload.is_required,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        depends_on_option_id=payload.depends_on_option_id,
        depends_on_value_id=payload.depends_on_value_id,
    )


async def update_lot_page_block(
    *,
    lot_id: int,
    block_id: int,
    payload: UpdateLotPageBlockRequest,
) -> ServicePage:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(block_id, field_label="Block id")

    page = await _get_lot_page_or_raise(lot_id, with_blocks=True)
    block = next((item for item in page.blocks if item.id == block_id), None)
    if block is None:
        raise LotPageBlockNotFoundError("Lot page block not found.")

    edit_lot_page_block_bl(
        block=block,
        payload_json=payload.payload_json,
    )

    _mark_page_as_draft(page)
    await s.db.flush()
    return await _get_lot_page_or_raise(lot_id)


async def upsert_lot_page(
    *,
    lot_id: int,
    payload: UpsertLotPageRequest,
) -> ServicePage:
    return await service_upsert_lot_page(
        lot_id=lot_id,
        title=payload.title,
        meta_json=payload.meta_json,
    )


async def change_lot_page_status(
    *,
    lot_id: int,
    payload: ChangeLotPageStatusRequest,
) -> ServicePage:
    return await service_change_lot_page_status(
        lot_id=lot_id,
        status=payload.status,
    )


async def create_lot_page_block(
    *,
    lot_id: int,
    payload: CreateLotPageBlockRequest,
) -> ServicePage:
    return await service_create_lot_page_block(
        lot_id=lot_id,
        block_type=payload.type,
        payload_json=payload.payload_json,
        position=payload.position,
    )


async def update_lot_option_value(
    *,
    lot_id: int,
    option_id: int,
    value_id: int,
    payload: UpdateLotOptionValueRequest,
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

    label = _resolve_nullable_required_field(
        payload.label,
        required_error_message="Option value label is required.",
    )
    code = _resolve_nullable_required_field(
        payload.code,
        required_error_message="Option value code is required.",
    )
    price_value = _resolve_nullable_required_field(
        payload.price_value,
        required_error_message="Option value price_value is required.",
    )
    is_default = _resolve_nullable_required_field(
        payload.is_default,
        required_error_message="Option value is_default is required.",
    )
    is_active = _resolve_nullable_required_field(
        payload.is_active,
        required_error_message="Option value is_active is required.",
    )

    scope = edit_lot_option_value_bl(
        value=value,
        label=label,
        code=code,
        description=payload.description,
        price_value=price_value,
        is_default=is_default,
        is_active=is_active,
    )

    if scope.should_check_code_scope:
        if await _lot_option_value_code_exists_in_scope(
            option_id=option.id,
            code=scope.code,
            exclude_value_id=value.id,
        ):
            raise LotOptionValueAlreadyExistsError(
                "Option value with this code already exists in this option."
            )

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_option_value_scope_code_conflict(exc):
            raise LotOptionValueAlreadyExistsError(
                "Option value with this code already exists in this option."
            ) from exc
        raise

    return await _get_lot_option_or_raise(
        lot_id=option.lot_id,
        option_id=option.id,
        with_values=True,
    )


async def create_lot_option_value(
    *,
    lot_id: int,
    option_id: int,
    payload: CreateLotOptionValueRequest,
) -> LotOption:
    return await service_create_lot_option_value(
        lot_id=lot_id,
        option_id=option_id,
        label=payload.label,
        code=payload.code,
        description=payload.description,
        price_value=payload.price_value,
        sort_order=payload.sort_order,
        is_default=payload.is_default,
        is_active=payload.is_active,
    )


async def soft_delete_lot(
    *,
    lot_id: int,
) -> ServiceLot:
    return await service_soft_delete_lot(lot_id=lot_id)


async def restore_lot(
    *,
    lot_id: int,
) -> ServiceLot:
    return await service_restore_lot(lot_id=lot_id)


async def delete_lot_option(
    *,
    lot_id: int,
    option_id: int,
) -> list[LotOption]:
    return await service_delete_lot_option(
        lot_id=lot_id,
        option_id=option_id,
    )


async def delete_lot_page_block(
    *,
    lot_id: int,
    block_id: int,
) -> ServicePage:
    return await service_delete_lot_page_block(
        lot_id=lot_id,
        block_id=block_id,
    )


async def delete_lot_option_value(
    *,
    lot_id: int,
    option_id: int,
    value_id: int,
) -> LotOption:
    return await service_delete_lot_option_value(
        lot_id=lot_id,
        option_id=option_id,
        value_id=value_id,
    )


async def reorder_lot_options(
    *,
    lot_id: int,
    payload: ReorderLotOptionsRequest,
) -> list[LotOption]:
    _validate_positive_id(lot_id, field_label="Lot id")

    lot = await _get_lot_by_id(lot_id)
    if lot is None:
        raise LotNotFoundError("Lot not found.")

    options = await _list_lot_options_by_lot_id(
        lot_id=lot.id,
        with_values=True,
    )
    scope_ids = [option.id for option in options]
    _validate_full_reorder_ids(
        scope_ids=scope_ids,
        requested_ids=payload.ids,
        entity_label="Lot options",
    )

    options_by_id = {option.id: option for option in options}
    for index, option_id in enumerate(payload.ids):
        options_by_id[option_id].sort_order = index

    if payload.ids:
        await s.db.flush()

    return await _list_lot_options_by_lot_id(
        lot_id=lot.id,
        with_values=True,
    )


async def reorder_lot_option_values(
    *,
    lot_id: int,
    option_id: int,
    payload: ReorderLotOptionValuesRequest,
) -> LotOption:
    _validate_positive_id(lot_id, field_label="Lot id")
    _validate_positive_id(option_id, field_label="Option id")

    option = await _get_lot_option_or_raise(
        lot_id=lot_id,
        option_id=option_id,
        with_values=True,
    )
    values = sorted(
        option.values,
        key=lambda value: (value.sort_order, value.id),
    )
    scope_ids = [value.id for value in values]
    _validate_full_reorder_ids(
        scope_ids=scope_ids,
        requested_ids=payload.ids,
        entity_label="Lot option values",
    )

    values_by_id = {value.id: value for value in values}
    for index, value_id in enumerate(payload.ids):
        values_by_id[value_id].sort_order = index

    if payload.ids:
        await s.db.flush()

    return await _get_lot_option_or_raise(
        lot_id=option.lot_id,
        option_id=option.id,
        with_values=True,
    )


async def reorder_lot_page_blocks(
    *,
    lot_id: int,
    payload: ReorderLotPageBlocksRequest,
) -> ServicePage:
    _validate_positive_id(lot_id, field_label="Lot id")

    page = await _get_lot_page_or_raise(lot_id, with_blocks=True)
    ordered_blocks = _ordered_page_blocks(page)
    scope_ids = [block.id for block in ordered_blocks]
    _validate_full_reorder_ids(
        scope_ids=scope_ids,
        requested_ids=payload.ids,
        entity_label="Lot page blocks",
    )

    if payload.ids != scope_ids:
        blocks_by_id = {block.id: block for block in ordered_blocks}
        reordered_blocks = [blocks_by_id[block_id] for block_id in payload.ids]
        _mark_page_as_draft(page)
        await _reindex_page_blocks(reordered_blocks)

    return await _get_lot_page_or_raise(lot_id)
