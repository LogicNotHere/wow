from __future__ import annotations

from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select
from sqlalchemy.orm import aliased

from wow_shop.infrastructure.db.session import s
from wow_shop.modules.catalog.constants import (
    CATEGORY_SLUG_PATTERN,
    CATEGORY_SCOPE_SLUG_CONSTRAINTS,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    CategoryNotFoundError,
    CategoryAlreadyExistsError,
    GameNotFoundError,
    ParentCategoryNotFoundError,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    ServiceCategory,
    ServiceCategoryStatus,
)
from wow_shop.shared.utils.missing import Missing, MissingType
from wow_shop.shared.utils.time import now_utc


def _normalize_name(name: str) -> str:
    normalized_name = name.strip()
    if not normalized_name:
        raise CatalogValidationError("Category name is required.")
    return normalized_name


def _normalize_slug(slug: str) -> str:
    normalized_slug = slug.strip().lower()
    if not normalized_slug:
        raise CatalogValidationError("Category slug is required.")
    if not CATEGORY_SLUG_PATTERN.fullmatch(normalized_slug):
        raise CatalogValidationError(
            "Category slug must contain lowercase letters, digits, "
            "hyphens, or underscores."
        )
    return normalized_slug


def _validate_parent_id(parent_id: int | None) -> None:
    if parent_id is not None and parent_id <= 0:
        raise CatalogValidationError("Parent id must be a positive integer.")


def _validate_game_id(game_id: int) -> None:
    if game_id <= 0:
        raise CatalogValidationError("Game id must be a positive integer.")


def _validate_non_negative_sort_order(sort_order: int) -> None:
    if sort_order < 0:
        raise CatalogValidationError(
            "Category sort_order must be greater than or equal to 0."
        )


def _validate_category_status_transition(
    *,
    current_status: ServiceCategoryStatus,
    target_status: ServiceCategoryStatus,
    via_soft_delete: bool = False,
) -> None:
    if current_status == target_status:
        return

    if via_soft_delete:
        allowed_transitions = {
            ServiceCategoryStatus.DRAFT: {ServiceCategoryStatus.DELETED},
            ServiceCategoryStatus.ACTIVE: {ServiceCategoryStatus.DELETED},
            ServiceCategoryStatus.INACTIVE: {ServiceCategoryStatus.DELETED},
            ServiceCategoryStatus.DELETED: {ServiceCategoryStatus.DELETED},
        }
        via_label = "soft delete"
    else:
        allowed_transitions = {
            ServiceCategoryStatus.DRAFT: {
                ServiceCategoryStatus.ACTIVE,
                ServiceCategoryStatus.INACTIVE,
            },
            ServiceCategoryStatus.ACTIVE: {ServiceCategoryStatus.INACTIVE},
            ServiceCategoryStatus.INACTIVE: {ServiceCategoryStatus.ACTIVE},
            ServiceCategoryStatus.DELETED: {ServiceCategoryStatus.INACTIVE},
        }
        via_label = "patch"

    allowed_targets = allowed_transitions.get(current_status, set())
    if target_status not in allowed_targets:
        raise CatalogValidationError(
            "Category status transition from "
            f"{current_status.name} to {target_status.name} "
            f"is not allowed via {via_label}."
        )


def _validate_category_active_game_invariant(
    *,
    target_status: ServiceCategoryStatus,
    game_is_active: bool,
) -> None:
    if (
        target_status == ServiceCategoryStatus.ACTIVE
        and not game_is_active
    ):
        raise CatalogValidationError(
            "Category cannot be ACTIVE while game is not ACTIVE."
        )


async def _get_game_by_id(game_id: int) -> Game | None:
    query = select(Game).where(Game.id == game_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def is_game_active(
    *,
    game_id: int,
) -> bool:
    game = await _get_game_by_id(game_id)
    return game is not None and game.status == GameStatus.ACTIVE


async def _get_category_by_id(category_id: int) -> ServiceCategory | None:
    query = select(ServiceCategory).where(ServiceCategory.id == category_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def is_descendant_category(
    *,
    candidate_parent: ServiceCategory,
    category: ServiceCategory,
) -> bool:
    current_id: int | None = candidate_parent.id
    visited_ids: set[int] = set()

    while current_id is not None:
        if current_id == category.id:
            return True

        # Guard against corrupted/cyclic data to avoid endless traversal.
        if current_id in visited_ids:
            return False
        visited_ids.add(current_id)

        current_category = await _get_category_by_id(current_id)
        if current_category is None:
            return False
        current_id = current_category.parent_id

    return False


async def _category_exists_in_scope(
    slug: str,
    parent_id: int | None,
    game_id: int,
    exclude_category_id: int | None = None,
) -> bool:
    query = select(ServiceCategory.id).where(
        ServiceCategory.game_id == game_id,
        ServiceCategory.slug == slug,
    )
    if parent_id is None:
        query = query.where(ServiceCategory.parent_id.is_(None))
    else:
        query = query.where(ServiceCategory.parent_id == parent_id)
    if exclude_category_id is not None:
        query = query.where(ServiceCategory.id != exclude_category_id)

    result = await s.db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def list_categories(
    *,
    game_id: int | None = None,
    include_inactive: bool = False,
) -> list[ServiceCategory]:
    query = select(ServiceCategory).join(ServiceCategory.game)
    if game_id is not None:
        query = query.where(ServiceCategory.game_id == game_id)
    if not include_inactive:
        query = query.where(
            ServiceCategory.status == ServiceCategoryStatus.ACTIVE,
            Game.status == GameStatus.ACTIVE,
        )

    query = query.order_by(
        ServiceCategory.game_id.asc(),
        ServiceCategory.sort_order.asc(),
        ServiceCategory.id.asc(),
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())


def apply_public_category_visibility(
    query: Select[tuple[ServiceCategory]],
) -> Select[tuple[ServiceCategory]]:
    category_ancestors = (
        select(
            ServiceCategory.id.label("category_id"),
            ServiceCategory.parent_id.label("ancestor_id"),
        )
        .cte("category_ancestors", recursive=True)
    )
    ancestor = aliased(ServiceCategory, name="ancestor_category")
    category_ancestors = category_ancestors.union_all(
        select(
            category_ancestors.c.category_id,
            ancestor.parent_id.label("ancestor_id"),
        )
        .select_from(ancestor)
        .join(
            category_ancestors,
            ancestor.id == category_ancestors.c.ancestor_id,
        )
    )

    non_active_ancestor_category_ids = (
        select(category_ancestors.c.category_id)
        .select_from(category_ancestors)
        .join(ancestor, ancestor.id == category_ancestors.c.ancestor_id)
        .where(ancestor.status != ServiceCategoryStatus.ACTIVE)
        .distinct()
    )

    return query.where(
        ServiceCategory.id.not_in(non_active_ancestor_category_ids)
    )


def _is_scope_slug_conflict(exc: IntegrityError) -> bool:
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

    if constraint_name in CATEGORY_SCOPE_SLUG_CONSTRAINTS:
        return True

    original_message = str(original_error)
    return any(
        constraint in original_message
        for constraint in CATEGORY_SCOPE_SLUG_CONSTRAINTS
    )


async def create_category(
    *,
    game_id: int,
    name: str,
    slug: str,
    parent_id: int | None,
    status: ServiceCategoryStatus,
    sort_order: int,
) -> ServiceCategory:
    _validate_game_id(game_id)
    normalized_name = _normalize_name(name)
    normalized_slug = _normalize_slug(slug)
    _validate_parent_id(parent_id)
    _validate_non_negative_sort_order(sort_order)
    if status == ServiceCategoryStatus.DELETED:
        raise CatalogValidationError(
            "Category cannot be created with DELETED status."
        )

    game = await _get_game_by_id(game_id)
    if game is None:
        raise GameNotFoundError("Game not found.")
    _validate_category_active_game_invariant(
        target_status=status,
        game_is_active=game.status == GameStatus.ACTIVE,
    )

    if parent_id is not None:
        parent = await _get_category_by_id(parent_id)
        if parent is None or parent.game_id != game.id:
            raise ParentCategoryNotFoundError(
                "Parent category not found in selected game."
            )

    if await _category_exists_in_scope(
        normalized_slug,
        parent_id,
        game.id,
    ):
        raise CategoryAlreadyExistsError(
            "Category with this slug already exists in this scope."
        )

    category = ServiceCategory(
        game_id=game.id,
        name=normalized_name,
        slug=normalized_slug,
        parent_id=parent_id,
        status=status,
        sort_order=sort_order,
    )
    s.db.add(category)

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_scope_slug_conflict(exc):
            raise CategoryAlreadyExistsError(
                "Category with this slug already exists in this scope."
            ) from exc
        raise

    return category


class CategoryEditScope(NamedTuple):
    game_id: int
    parent_id: int | None
    slug: str
    should_check_slug_scope: bool


def edit_category_bl(
    *,
    category: ServiceCategory,
    game_is_active: bool,
    name: str | MissingType,
    slug: str | MissingType,
    parent: ServiceCategory | None | MissingType,
    status: ServiceCategoryStatus | MissingType,
    sort_order: int | MissingType,
) -> CategoryEditScope:
    if not any(
        (
            name is not Missing,
            slug is not Missing,
            parent is not Missing,
            status is not Missing,
            sort_order is not Missing,
        )
    ):
        raise CatalogValidationError(
            "At least one field must be provided for category update."
        )

    target_parent_id = category.parent_id
    target_slug = category.slug
    should_check_slug_scope = False

    if name is not Missing:
        category.name = _normalize_name(name)

    if slug is not Missing:
        target_slug = _normalize_slug(slug)
        category.slug = target_slug
        should_check_slug_scope = True

    if parent is not Missing:
        if parent is not None and parent.id == category.id:
            raise CatalogValidationError("Category cannot be its own parent.")
        target_parent_id = parent.id if parent is not None else None
        category.parent_id = target_parent_id
        should_check_slug_scope = True

    if status is not Missing:
        _validate_category_status_transition(
            current_status=category.status,
            target_status=status,
            via_soft_delete=False,
        )
        _validate_category_active_game_invariant(
            target_status=status,
            game_is_active=game_is_active,
        )
        category.status = status

    if sort_order is not Missing:
        _validate_non_negative_sort_order(sort_order)
        category.sort_order = sort_order

    if category.status == ServiceCategoryStatus.DELETED:
        if category.deleted_at is None:
            category.deleted_at = now_utc()
    else:
        category.deleted_at = None

    return CategoryEditScope(
        game_id=category.game_id,
        parent_id=target_parent_id,
        slug=target_slug,
        should_check_slug_scope=should_check_slug_scope,
    )


async def get_staff_category_by_id(
    *,
    category_id: int,
) -> ServiceCategory:
    category = await _get_category_by_id(category_id)
    if category is None:
        raise CategoryNotFoundError("Category not found.")
    return category


async def category_slug_exists_in_scope(
    *,
    slug: str,
    parent_id: int | None,
    game_id: int,
    exclude_category_id: int | None = None,
) -> bool:
    normalized_slug = _normalize_slug(slug)
    return await _category_exists_in_scope(
        slug=normalized_slug,
        parent_id=parent_id,
        game_id=game_id,
        exclude_category_id=exclude_category_id,
    )


def is_category_scope_slug_conflict(exc: IntegrityError) -> bool:
    return _is_scope_slug_conflict(exc)


async def soft_delete_category(
    *,
    category_id: int,
) -> ServiceCategory:
    category = await get_staff_category_by_id(category_id=category_id)

    _validate_category_status_transition(
        current_status=category.status,
        target_status=ServiceCategoryStatus.DELETED,
        via_soft_delete=True,
    )

    update_required = False
    if category.status != ServiceCategoryStatus.DELETED:
        category.status = ServiceCategoryStatus.DELETED
        update_required = True
    if category.deleted_at is None:
        category.deleted_at = now_utc()
        update_required = True

    if update_required:
        await s.db.flush()

    return category


async def restore_category(
    *,
    category_id: int,
) -> ServiceCategory:
    category = await get_staff_category_by_id(category_id=category_id)
    if category.status != ServiceCategoryStatus.DELETED:
        raise CatalogValidationError(
            "Category restore is allowed only from DELETED status."
        )

    category.status = ServiceCategoryStatus.INACTIVE
    category.deleted_at = None
    await s.db.flush()
    return category
