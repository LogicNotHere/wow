from __future__ import annotations

from fastapi import APIRouter, Depends, Path
from starlette import status

from wow_shop.api.dependencies.permissions import (
    require_catalog_restore_access,
    require_catalog_soft_delete_access,
)
from wow_shop.api.responses import ErrorResponseModel
from wow_shop.shared.contracts import BaseHttpResponseModel, ListResponsesOnce
from wow_shop.modules.catalog.api.query.categories_query import (
    GetCategoriesQueryModel,
    get_categories_query_model,
)
from wow_shop.modules.catalog.api.request.category_models import (
    CreateCategoryRequest,
    PatchCategoryRequest,
)
from wow_shop.modules.catalog.api.response.category_models import (
    CategoryCreatedResponse,
    CategoryListItemResponse,
    CategoryTreeItemResponse,
    build_category_tree,
)
from wow_shop.modules.catalog.application.category_commands import (
    create_category,
    patch_category,
    restore_category,
    soft_delete_category,
)
from wow_shop.shared.types import IntId

public_router = APIRouter(prefix="/categories", tags=["categories"])
staff_router = APIRouter(prefix="/categories", tags=["categories"])


@public_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Read catalog service categories list.",
    response_model=BaseHttpResponseModel[
        ListResponsesOnce[CategoryTreeItemResponse]
    ],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[CategoryTreeItemResponse]
            ],
            "description": "Category list.",
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
async def get_categories_route(
    query_model: GetCategoriesQueryModel = Depends(
        get_categories_query_model
    ),
) -> BaseHttpResponseModel[ListResponsesOnce[CategoryTreeItemResponse]]:
    categories = await query_model.get_items()
    category_tree = build_category_tree(categories)
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(items=category_tree),
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
    category = await create_category(payload=payload)
    return BaseHttpResponseModel(
        data=CategoryCreatedResponse.build(category.id),
        message="Category created.",
    )


@staff_router.patch(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    description="Patch catalog service category.",
    response_model=BaseHttpResponseModel[CategoryListItemResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[CategoryListItemResponse],
            "description": "Category updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid category patch input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Category not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Category slug conflict in selected scope.",
        },
    },
)
async def patch_category_route(
    payload: PatchCategoryRequest,
    category_id: IntId = Path(),
) -> BaseHttpResponseModel[CategoryListItemResponse]:
    category = await patch_category(
        category_id=category_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=CategoryListItemResponse.build(category),
        message="Category updated.",
    )


@staff_router.delete(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    description="Soft delete catalog service category.",
    dependencies=[Depends(require_catalog_soft_delete_access)],
    response_model=BaseHttpResponseModel[CategoryListItemResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[CategoryListItemResponse],
            "description": "Category soft-deleted.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Category not found.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponseModel,
            "description": "Not enough permissions.",
        },
    },
)
async def soft_delete_category_route(
    category_id: IntId = Path(),
) -> BaseHttpResponseModel[CategoryListItemResponse]:
    category = await soft_delete_category(category_id=category_id)
    return BaseHttpResponseModel(
        data=CategoryListItemResponse.build(category),
        message="Category deleted.",
    )


@staff_router.post(
    "/{category_id}/restore",
    status_code=status.HTTP_200_OK,
    description="Restore soft-deleted category to INACTIVE status.",
    dependencies=[Depends(require_catalog_restore_access)],
    response_model=BaseHttpResponseModel[CategoryListItemResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[CategoryListItemResponse],
            "description": "Category restored.",
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
            "description": "Category not found.",
        },
    },
)
async def restore_category_route(
    category_id: IntId = Path(),
) -> BaseHttpResponseModel[CategoryListItemResponse]:
    category = await restore_category(category_id=category_id)
    return BaseHttpResponseModel(
        data=CategoryListItemResponse.build(category),
        message="Category restored.",
    )
