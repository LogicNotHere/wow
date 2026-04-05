from __future__ import annotations

from typing import TypeVar

from sqlalchemy.exc import IntegrityError

from wow_shop.modules.catalog.api.request.category_models import (
    CreateCategoryRequest,
    PatchCategoryRequest,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    CategoryAlreadyExistsError,
    CategoryNotFoundError,
    ParentCategoryNotFoundError,
)
from wow_shop.modules.catalog.application.category_service import (
    category_slug_exists_in_scope,
    create_category as service_create_category,
    edit_category_bl,
    get_staff_category_by_id,
    is_game_active,
    is_descendant_category,
    restore_category as service_restore_category,
    is_category_scope_slug_conflict,
    soft_delete_category as service_soft_delete_category,
)
from wow_shop.modules.catalog.infrastructure.db.models import ServiceCategory
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


async def _resolve_patch_parent(
    *,
    category: ServiceCategory,
    parent_id: int | None | MissingType,
) -> ServiceCategory | None | MissingType:
    if parent_id is Missing:
        return Missing
    if parent_id is None:
        return None

    try:
        parent = await get_staff_category_by_id(category_id=parent_id)
    except CategoryNotFoundError as exc:
        raise ParentCategoryNotFoundError(
            "Parent category not found in selected game."
        ) from exc
    if parent.game_id != category.game_id:
        raise ParentCategoryNotFoundError(
            "Parent category not found in selected game."
        )
    if parent.id != category.id and await is_descendant_category(
        candidate_parent=parent,
        category=category,
    ):
        raise CatalogValidationError(
            "Category cannot be moved under its own descendant."
        )
    return parent


async def create_category(
    *,
    payload: CreateCategoryRequest,
) -> ServiceCategory:
    return await service_create_category(
        game_id=payload.game_id,
        name=payload.name,
        slug=payload.slug,
        parent_id=payload.parent_id,
        status=payload.status,
        sort_order=payload.sort_order,
    )


async def patch_category(
    *,
    category_id: int,
    payload: PatchCategoryRequest,
) -> ServiceCategory:
    category = await get_staff_category_by_id(category_id=category_id)

    name = _resolve_nullable_required_field(
        payload.name,
        required_error_message="Category name is required.",
    )
    slug = _resolve_nullable_required_field(
        payload.slug,
        required_error_message="Category slug is required.",
    )
    status = _resolve_nullable_required_field(
        payload.status,
        required_error_message="Category status is required.",
    )
    sort_order = _resolve_nullable_required_field(
        payload.sort_order,
        required_error_message="Category sort_order is required.",
    )
    resolved_parent = await _resolve_patch_parent(
        category=category,
        parent_id=payload.parent_id,
    )

    scope = edit_category_bl(
        category=category,
        game_is_active=await is_game_active(game_id=category.game_id),
        name=name,
        slug=slug,
        parent=resolved_parent,
        status=status,
        sort_order=sort_order,
    )

    if scope.should_check_slug_scope:
        if await category_slug_exists_in_scope(
            slug=scope.slug,
            parent_id=scope.parent_id,
            game_id=scope.game_id,
            exclude_category_id=category.id,
        ):
            raise CategoryAlreadyExistsError(
                "Category with this slug already exists in this scope."
            )

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if is_category_scope_slug_conflict(exc):
            raise CategoryAlreadyExistsError(
                "Category with this slug already exists in this scope."
            ) from exc
        raise

    return category


async def soft_delete_category(
    *,
    category_id: int,
) -> ServiceCategory:
    return await service_soft_delete_category(category_id=category_id)


async def restore_category(
    *,
    category_id: int,
) -> ServiceCategory:
    return await service_restore_category(category_id=category_id)
