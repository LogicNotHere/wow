from fastapi import APIRouter, Depends, Path
from starlette import status

from wow_shop.api.dependencies.permissions import (
    require_catalog_restore_access,
    require_catalog_soft_delete_access,
)
from wow_shop.api.responses import ErrorResponseModel
from wow_shop.shared.contracts import BaseHttpResponseModel, ListResponsesOnce
from wow_shop.modules.catalog.api.query.games_query import (
    GetGamesQueryModel,
    get_games_query_model,
)
from wow_shop.modules.catalog.api.request.game_models import (
    CreateGameRequest,
    GameSlug,
    PatchGameRequest,
    ReorderGamesRequest,
)
from wow_shop.modules.catalog.api.response.game_models import (
    GameCreatedResponse,
    GameDetailResponse,
    GameListItemResponse,
)
from wow_shop.modules.catalog.application.game_commands import (
    create_game,
    patch_game,
    reorder_games,
    restore_game,
    soft_delete_game,
)
from wow_shop.modules.catalog.application.game_service import (
    get_staff_game_by_slug,
)

public_router = APIRouter(prefix="/games", tags=["games"])
staff_router = APIRouter(prefix="/games", tags=["games"])


@public_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Read catalog games list.",
    response_model=BaseHttpResponseModel[ListResponsesOnce[GameListItemResponse]],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[GameListItemResponse]
            ],
            "description": "Game list.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid status filter for current access mode.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponseModel,
            "description": "Invalid authorization token.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponseModel,
            "description": "Not enough permissions.",
        },
    },
)
async def get_games_route(
    query_model: GetGamesQueryModel = Depends(get_games_query_model),
) -> BaseHttpResponseModel[ListResponsesOnce[GameListItemResponse]]:
    games = await query_model.get_items()
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[GameListItemResponse.build(game) for game in games]
        ),
        message="Games fetched.",
    )


@staff_router.get(
    "/{game_slug}",
    status_code=status.HTTP_200_OK,
    description="Read staff game detail by slug.",
    response_model=BaseHttpResponseModel[GameDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[GameDetailResponse],
            "description": "Game fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Game not found.",
        },
    },
)
async def get_staff_game_by_slug_route(
    game_slug: GameSlug = Path(),
) -> BaseHttpResponseModel[GameDetailResponse]:
    game = await get_staff_game_by_slug(game_slug=game_slug)
    return BaseHttpResponseModel(
        data=GameDetailResponse.build(game),
        message="Game fetched.",
    )


@staff_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    description="Create catalog game.",
    response_model=BaseHttpResponseModel[GameCreatedResponse],
    responses={
        status.HTTP_201_CREATED: {
            "model": BaseHttpResponseModel[GameCreatedResponse],
            "description": "Game created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid game input.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Game slug conflict.",
        },
    },
)
async def create_game_route(
    payload: CreateGameRequest,
) -> BaseHttpResponseModel[GameCreatedResponse]:
    game = await create_game(payload=payload)
    return BaseHttpResponseModel(
        data=GameCreatedResponse.build(game.id),
        message="Game created.",
    )


@staff_router.patch(
    "/reorder",
    status_code=status.HTTP_200_OK,
    description="Reorder games.",
    response_model=BaseHttpResponseModel[ListResponsesOnce[GameListItemResponse]],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[GameListItemResponse]
            ],
            "description": "Games reordered.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid games reorder payload.",
        },
    },
)
async def reorder_games_route(
    payload: ReorderGamesRequest,
) -> BaseHttpResponseModel[ListResponsesOnce[GameListItemResponse]]:
    games = await reorder_games(payload=payload)
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[GameListItemResponse.build(game) for game in games]
        ),
        message="Games reordered.",
    )


@staff_router.patch(
    "/{game_slug}",
    status_code=status.HTTP_200_OK,
    description="Patch game.",
    response_model=BaseHttpResponseModel[GameDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[GameDetailResponse],
            "description": "Game updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid game input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Game not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Game slug conflict.",
        },
    },
)
async def patch_game_route(
    payload: PatchGameRequest,
    game_slug: GameSlug = Path(),
) -> BaseHttpResponseModel[GameDetailResponse]:
    game = await patch_game(game_slug=game_slug, payload=payload)
    return BaseHttpResponseModel(
        data=GameDetailResponse.build(game),
        message="Game updated.",
    )


@staff_router.delete(
    "/{game_slug}",
    status_code=status.HTTP_200_OK,
    description="Soft delete game.",
    dependencies=[Depends(require_catalog_soft_delete_access)],
    response_model=BaseHttpResponseModel[GameDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[GameDetailResponse],
            "description": "Game soft-deleted.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Game not found.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponseModel,
            "description": "Not enough permissions.",
        },
    },
)
async def soft_delete_game_route(
    game_slug: GameSlug = Path(),
) -> BaseHttpResponseModel[GameDetailResponse]:
    game = await soft_delete_game(game_slug=game_slug)
    return BaseHttpResponseModel(
        data=GameDetailResponse.build(game),
        message="Game deleted.",
    )


@staff_router.post(
    "/{game_slug}/restore",
    status_code=status.HTTP_200_OK,
    description="Restore soft-deleted game to INACTIVE status.",
    dependencies=[Depends(require_catalog_restore_access)],
    response_model=BaseHttpResponseModel[GameDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[GameDetailResponse],
            "description": "Game restored.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid restore transition.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponseModel,
            "description": "Not enough permissions.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Game not found.",
        },
    },
)
async def restore_game_route(
    game_slug: GameSlug = Path(),
) -> BaseHttpResponseModel[GameDetailResponse]:
    game = await restore_game(game_slug=game_slug)
    return BaseHttpResponseModel(
        data=GameDetailResponse.build(game),
        message="Game restored.",
    )
