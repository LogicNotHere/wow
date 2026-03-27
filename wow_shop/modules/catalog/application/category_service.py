from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from wow_shop.infrastructure.db.session import s
from wow_shop.modules.catalog.constants import (
    CATEGORY_SLUG_PATTERN,
    CATEGORY_SCOPE_SLUG_CONSTRAINTS,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    CategoryAlreadyExistsError,
    GameNotFoundError,
    ParentCategoryNotFoundError,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    ServiceCategory,
)


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


async def _get_game_by_id(game_id: int) -> Game | None:
    query = select(Game).where(Game.id == game_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _get_category_by_id(category_id: int) -> ServiceCategory | None:
    query = select(ServiceCategory).where(ServiceCategory.id == category_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _category_exists_in_scope(
    slug: str,
    parent_id: int | None,
    game_id: int,
) -> bool:
    query = select(ServiceCategory.id).where(
        ServiceCategory.game_id == game_id,
        ServiceCategory.slug == slug,
    )
    if parent_id is None:
        query = query.where(ServiceCategory.parent_id.is_(None))
    else:
        query = query.where(ServiceCategory.parent_id == parent_id)

    result = await s.db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def list_categories(game_id: int | None = None) -> list[ServiceCategory]:
    query = select(ServiceCategory)
    if game_id is not None:
        query = query.where(ServiceCategory.game_id == game_id)

    query = query.order_by(
        ServiceCategory.game_id.asc(),
        ServiceCategory.sort_order.asc(),
        ServiceCategory.id.asc(),
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())


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
    is_active: bool,
    sort_order: int,
) -> ServiceCategory:
    _validate_game_id(game_id)
    normalized_name = _normalize_name(name)
    normalized_slug = _normalize_slug(slug)
    _validate_parent_id(parent_id)

    game = await _get_game_by_id(game_id)
    if game is None:
        raise GameNotFoundError("Game not found.")

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
        is_active=is_active,
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
