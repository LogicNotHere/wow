from __future__ import annotations

from datetime import datetime, timezone
from typing import NamedTuple

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
    GameNotFoundError,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
)
from wow_shop.shared.utils.missing import Missing, MissingType


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


def _validate_non_negative_sort_order(sort_order: int) -> None:
    if sort_order < 0:
        raise CatalogValidationError(
            "Game sort_order must be greater than or equal to 0."
        )


def _validate_game_status_transition(
    *,
    current_status: GameStatus,
    target_status: GameStatus,
    via_soft_delete: bool = False,
) -> None:
    if current_status == target_status:
        return

    if via_soft_delete:
        allowed_transitions = {
            GameStatus.DRAFT: {GameStatus.DELETED},
            GameStatus.ACTIVE: {GameStatus.DELETED},
            GameStatus.INACTIVE: {GameStatus.DELETED},
            GameStatus.DELETED: {GameStatus.DELETED},
        }
        via_label = "soft delete"
    else:
        allowed_transitions = {
            GameStatus.DRAFT: {
                GameStatus.ACTIVE,
                GameStatus.INACTIVE,
            },
            GameStatus.ACTIVE: {GameStatus.INACTIVE},
            GameStatus.INACTIVE: {GameStatus.ACTIVE},
            GameStatus.DELETED: {GameStatus.INACTIVE},
        }
        via_label = "patch"

    allowed_targets = allowed_transitions.get(current_status, set())
    if target_status not in allowed_targets:
        raise CatalogValidationError(
            "Game status transition from "
            f"{current_status.name} to {target_status.name} "
            f"is not allowed via {via_label}."
        )


def is_game_slug_conflict(exc: IntegrityError) -> bool:
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
    status: GameStatus,
    sort_order: int,
) -> Game:
    normalized_name = _normalize_name(name)
    normalized_slug = _normalize_slug(slug)
    _validate_non_negative_sort_order(sort_order)
    if status == GameStatus.DELETED:
        raise CatalogValidationError(
            "Game cannot be created with DELETED status."
        )

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
        status=status,
        sort_order=sort_order,
    )
    s.db.add(game)

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if is_game_slug_conflict(exc):
            raise GameAlreadyExistsError(
                "Game with this slug already exists."
            ) from exc
        raise

    return game


class GameEditScope(NamedTuple):
    slug: str
    should_check_slug_scope: bool


def edit_game_bl(
    *,
    game: Game,
    name: str | MissingType,
    slug: str | MissingType,
    status: GameStatus | MissingType,
    sort_order: int | MissingType,
) -> GameEditScope:
    if not any(
        (
            name is not Missing,
            slug is not Missing,
            status is not Missing,
            sort_order is not Missing,
        )
    ):
        raise CatalogValidationError(
            "At least one field must be provided for game update."
        )

    target_slug = game.slug
    should_check_slug_scope = False

    if name is not Missing:
        game.name = _normalize_name(name)

    if slug is not Missing:
        target_slug = _normalize_slug(slug)
        game.slug = target_slug
        should_check_slug_scope = True

    if status is not Missing:
        _validate_game_status_transition(
            current_status=game.status,
            target_status=status,
            via_soft_delete=False,
        )
        game.status = status

    if sort_order is not Missing:
        _validate_non_negative_sort_order(sort_order)
        game.sort_order = sort_order

    if game.status == GameStatus.DELETED:
        if game.deleted_at is None:
            game.deleted_at = datetime.now(timezone.utc)
    else:
        game.deleted_at = None

    return GameEditScope(
        slug=target_slug,
        should_check_slug_scope=should_check_slug_scope,
    )


async def list_games(
    *,
    include_inactive: bool = False,
) -> list[Game]:
    query = select(Game)
    if not include_inactive:
        query = query.where(Game.status == GameStatus.ACTIVE)

    query = query.order_by(
        Game.sort_order.asc(),
        Game.id.asc(),
    )
    result = await s.db.execute(query)
    return list(result.scalars().all())


async def soft_delete_game(
    *,
    game_slug: str,
) -> Game:
    game = await get_staff_game_by_slug(game_slug=game_slug)

    _validate_game_status_transition(
        current_status=game.status,
        target_status=GameStatus.DELETED,
        via_soft_delete=True,
    )

    update_required = False
    if game.status != GameStatus.DELETED:
        game.status = GameStatus.DELETED
        update_required = True
    if game.deleted_at is None:
        game.deleted_at = datetime.now(timezone.utc)
        update_required = True

    if update_required:
        await s.db.flush()

    return game


async def restore_game(
    *,
    game_slug: str,
) -> Game:
    game = await get_staff_game_by_slug(game_slug=game_slug)
    if game.status != GameStatus.DELETED:
        raise CatalogValidationError(
            "Game restore is allowed only from DELETED status."
        )

    game.status = GameStatus.INACTIVE
    game.deleted_at = None
    await s.db.flush()
    return game


async def get_staff_game_by_slug(
    *,
    game_slug: str,
) -> Game:
    normalized_slug = _normalize_slug(game_slug)
    query = select(Game).where(Game.slug == normalized_slug)
    result = await s.db.execute(query.limit(1))
    game = result.scalar_one_or_none()
    if game is None:
        raise GameNotFoundError("Game not found.")
    return game


async def game_slug_exists(
    *,
    slug: str,
    exclude_game_id: int | None = None,
) -> bool:
    normalized_slug = _normalize_slug(slug)
    query = select(Game.id).where(Game.slug == normalized_slug).limit(1)
    if exclude_game_id is not None:
        query = query.where(Game.id != exclude_game_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none() is not None
