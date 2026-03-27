from __future__ import annotations

from fastapi import APIRouter, Query
from starlette import status

from wow_shop.api.responses import ErrorResponseModel
from wow_shop.shared.contracts import BaseHttpResponseModel, ListResponsesOnce
from wow_shop.modules.catalog.api.request.category_models import (
    CreateCategoryRequest,
)
from wow_shop.modules.catalog.api.response.category_models import (
    CategoryCreatedResponse,
    CategoryListItemResponse,
)
from wow_shop.modules.catalog.application.category_service import (
    create_category,
    list_categories,
)

public_router = APIRouter(prefix="/categories", tags=["categories"])
staff_router = APIRouter(prefix="/categories", tags=["categories"])


@public_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Read catalog service categories list.",
    response_model=BaseHttpResponseModel[
        ListResponsesOnce[CategoryListItemResponse]
    ],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[CategoryListItemResponse]
            ],
            "description": "Category list.",
        },
    },
)
async def get_categories_route(
    game_id: int | None = Query(default=None, ge=1),
) -> BaseHttpResponseModel[ListResponsesOnce[CategoryListItemResponse]]:
    categories = await list_categories(game_id=game_id)
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            [CategoryListItemResponse.build(category) for category in categories]
        ),
        message="Categories fetched.",
    )


@staff_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    description="Create catalog service category.",
    response_model=BaseHttpResponseModel[CategoryCreatedResponse],
    responses={
        status.HTTP_201_CREATED: {
            "model": BaseHttpResponseModel[CategoryCreatedResponse],
            "description": "Category created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid category input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Game or parent category not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Category slug conflict in selected scope.",
        },
    },
)
async def create_category_route(
    payload: CreateCategoryRequest,
) -> BaseHttpResponseModel[CategoryCreatedResponse]:
    category = await create_category(
        game_id=payload.game_id,
        name=payload.name,
        slug=payload.slug,
        parent_id=payload.parent_id,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    return BaseHttpResponseModel(
        data=CategoryCreatedResponse.build(category.id),
        message="Category created.",
    )
