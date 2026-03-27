from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from wow_shop.infrastructure.db.session import s
from wow_shop.infrastructure.db.validators import get_existing_by_field
from wow_shop.modules.catalog.constants import (
    GAME_SLUG_CONSTRAINTS,
    GAME_SLUG_PATTERN,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    GameAlreadyExistsError,
)
from wow_shop.modules.catalog.infrastructure.db.models import Game


def _normalize_name(name: str) -> str:
    normalized_name = name.strip()
    if not normalized_name:
        raise CatalogValidationError("Game name is required.")
    return normalized_name


def _normalize_slug(slug: str) -> str:
    normalized_slug = slug.strip().lower()
    if not normalized_slug:
        raise CatalogValidationError("Game slug is required.")
    if not GAME_SLUG_PATTERN.fullmatch(normalized_slug):
        raise CatalogValidationError(
            "Game slug must contain lowercase letters, digits, "
            "hyphens, or underscores."
        )
    return normalized_slug


def _is_game_slug_conflict(exc: IntegrityError) -> bool:
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

    if constraint_name in GAME_SLUG_CONSTRAINTS:
        return True

    original_message = str(original_error)
    return any(
        constraint in original_message for constraint in GAME_SLUG_CONSTRAINTS
    )


async def create_game(
    *,
    name: str,
    slug: str,
    is_active: bool,
    sort_order: int,
) -> Game:
    normalized_name = _normalize_name(name)
    normalized_slug = _normalize_slug(slug)

    existing_game = await get_existing_by_field(
        session=s.db,
        model=Game,
        field=Game.slug,
        value=normalized_slug,
    )
    if existing_game is not None:
        raise GameAlreadyExistsError("Game with this slug already exists.")

    game = Game(
        name=normalized_name,
        slug=normalized_slug,
        is_active=is_active,
        sort_order=sort_order,
    )
    s.db.add(game)

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if _is_game_slug_conflict(exc):
            raise GameAlreadyExistsError(
                "Game with this slug already exists."
            ) from exc
        raise

    return game


async def list_games() -> list[Game]:
    query = select(Game).order_by(
        Game.sort_order.asc(),
        Game.id.asc(),
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())
