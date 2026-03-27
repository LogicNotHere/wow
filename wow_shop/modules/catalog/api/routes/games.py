from fastapi import APIRouter
from starlette import status

from wow_shop.api.responses import ErrorResponseModel
from wow_shop.shared.contracts import BaseHttpResponseModel, ListResponsesOnce
from wow_shop.modules.catalog.api.request.game_models import (
    CreateGameRequest,
)
from wow_shop.modules.catalog.api.response.game_models import (
    GameCreatedResponse,
    GameListItemResponse,
)
from wow_shop.modules.catalog.application.game_service import (
    create_game,
    list_games,
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
    },
)
async def get_games_route() -> BaseHttpResponseModel[
    ListResponsesOnce[GameListItemResponse]
]:
    games = await list_games()
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            [GameListItemResponse.build(game) for game in games]
        ),
        message="Games fetched.",
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
    game = await create_game(
        name=payload.name,
        slug=payload.slug,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    return BaseHttpResponseModel(
        data=GameCreatedResponse.build(game.id),
        message="Game created.",
    )
