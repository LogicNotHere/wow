from __future__ import annotations

from typing import TypeVar

from sqlalchemy.exc import IntegrityError

from wow_shop.modules.catalog.api.request.game_models import (
    CreateGameRequest,
    PatchGameRequest,
    ReorderGamesRequest,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    GameAlreadyExistsError,
)
from wow_shop.modules.catalog.application.game_service import (
    create_game as service_create_game,
    edit_game_bl,
    game_slug_exists,
    get_staff_game_by_slug,
    is_game_slug_conflict,
    list_games,
    restore_game as service_restore_game,
    soft_delete_game as service_soft_delete_game,
)
from wow_shop.modules.catalog.infrastructure.db.models import Game
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


async def create_game(
    *,
    payload: CreateGameRequest,
) -> Game:
    return await service_create_game(
        name=payload.name,
        slug=payload.slug,
        status=payload.status,
        sort_order=payload.sort_order,
    )


async def patch_game(
    *,
    game_slug: str,
    payload: PatchGameRequest,
) -> Game:
    game = await get_staff_game_by_slug(game_slug=game_slug)

    name = _resolve_nullable_required_field(
        payload.name,
        required_error_message="Game name is required.",
    )
    slug = _resolve_nullable_required_field(
        payload.slug,
        required_error_message="Game slug is required.",
    )
    status = _resolve_nullable_required_field(
        payload.status,
        required_error_message="Game status is required.",
    )
    sort_order = _resolve_nullable_required_field(
        payload.sort_order,
        required_error_message="Game sort_order is required.",
    )

    scope = edit_game_bl(
        game=game,
        name=name,
        slug=slug,
        status=status,
        sort_order=sort_order,
    )

    if scope.should_check_slug_scope:
        if await game_slug_exists(
            slug=scope.slug,
            exclude_game_id=game.id,
        ):
            raise GameAlreadyExistsError("Game with this slug already exists.")

    try:
        await s.db.flush()
    except IntegrityError as exc:
        if is_game_slug_conflict(exc):
            raise GameAlreadyExistsError(
                "Game with this slug already exists."
            ) from exc
        raise

    return game


async def reorder_games(
    *,
    payload: ReorderGamesRequest,
) -> list[Game]:
    games = await list_games(include_inactive=True)
    scope_ids = [game.id for game in games]
    _validate_full_reorder_ids(
        scope_ids=scope_ids,
        requested_ids=payload.ids,
        entity_label="Games",
    )

    if payload.ids != scope_ids:
        games_by_id = {game.id: game for game in games}
        for index, game_id in enumerate(payload.ids):
            games_by_id[game_id].sort_order = index
        if payload.ids:
            await s.db.flush()

    return await list_games(include_inactive=True)


async def soft_delete_game(
    *,
    game_slug: str,
) -> Game:
    return await service_soft_delete_game(game_slug=game_slug)


async def restore_game(
    *,
    game_slug: str,
) -> Game:
    return await service_restore_game(game_slug=game_slug)
