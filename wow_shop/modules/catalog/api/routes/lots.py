from __future__ import annotations

from fastapi import APIRouter, Depends, Path
from starlette import status

from wow_shop.api.dependencies.permissions import (
    require_catalog_restore_access,
    require_catalog_soft_delete_access,
)
from wow_shop.api.responses import ErrorResponseModel
from wow_shop.modules.catalog.api.query.lots_query import (
    GetLotOptionQueryModel,
    GetLotOptionsQueryModel,
    GetLotPageQueryModel,
    GetPublicLotsQueryModel,
    GetStaffLotsQueryModel,
    get_lot_page_query_model,
    get_public_lots_query_model,
    get_staff_lot_option_query_model,
    get_staff_lot_options_query_model,
    get_staff_lots_query_model,
)
from wow_shop.modules.catalog.api.request.category_models import CategorySlug
from wow_shop.modules.catalog.api.request.game_models import GameSlug
from wow_shop.modules.catalog.api.request.lot_models import (
    ChangeLotPageStatusRequest,
    CreateLotOptionRequest,
    CreateLotOptionValueRequest,
    CreateLotPageBlockRequest,
    CreateLotRequest,
    PatchLotRequest,
    ReorderLotOptionValuesRequest,
    ReorderLotOptionsRequest,
    ReorderLotPageBlocksRequest,
    LotSlug,
    UpsertLotPageRequest,
    UpdateLotOptionRequest,
    UpdateLotOptionValueRequest,
    UpdateLotPageBlockRequest,
)
from wow_shop.modules.catalog.api.response.lot_models import (
    LotCreatedResponse,
    LotDetailResponse,
    LotListItemResponse,
    LotOptionResponse,
    LotPageResponse,
    StaffLotListItemResponse,
)
from wow_shop.modules.catalog.application.lot_service import (
    get_public_lot_by_slugs,
    get_staff_lot_by_slugs,
)
from wow_shop.modules.catalog.application.lot_commands import (
    change_lot_page_status,
    create_lot_option,
    create_lot_option_value,
    create_lot_page_block,
    create_lot,
    delete_lot_option,
    delete_lot_option_value,
    delete_lot_page_block,
    patch_lot,
    reorder_lot_option_values,
    reorder_lot_options,
    reorder_lot_page_blocks,
    restore_lot,
    soft_delete_lot,
    upsert_lot_page,
    update_lot_option,
    update_lot_option_value,
    update_lot_page_block,
)
from wow_shop.shared.contracts import BaseHttpResponseModel, ListResponsesOnce
from wow_shop.shared.types import IntId

public_router = APIRouter(prefix="/lots", tags=["lots"])
staff_router = APIRouter(prefix="/lots", tags=["lots"])


# ---------------------------
# Lot
# ---------------------------
@public_router.get(
    "/{game_slug}/{category_slug}",
    status_code=status.HTTP_200_OK,
    description="Read public catalog lots list by game/category slugs.",
    response_model=BaseHttpResponseModel[ListResponsesOnce[LotListItemResponse]],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[LotListItemResponse]
            ],
            "description": "Lot list.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Game or category not found.",
        },
    },
)
async def get_lots_route(
    query_model: GetPublicLotsQueryModel = Depends(get_public_lots_query_model),
) -> BaseHttpResponseModel[ListResponsesOnce[LotListItemResponse]]:
    lots = await query_model.get_items()
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[LotListItemResponse.build(lot) for lot in lots]
        ),
        message="Lots fetched.",
    )


@public_router.get(
    "/{game_slug}/{category_slug}/{lot_slug}",
    status_code=status.HTTP_200_OK,
    description="Read public catalog lot by game/category/lot slugs.",
    response_model=BaseHttpResponseModel[LotDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotDetailResponse],
            "description": "Lot fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot not found.",
        },
    },
)
async def get_lot_by_slug_route(
    game_slug: GameSlug = Path(),
    category_slug: CategorySlug = Path(),
    lot_slug: LotSlug = Path(),
) -> BaseHttpResponseModel[LotDetailResponse]:
    lot = await get_public_lot_by_slugs(
        game_slug=game_slug,
        category_slug=category_slug,
        lot_slug=lot_slug,
    )
    return BaseHttpResponseModel(
        data=LotDetailResponse.build(lot),
        message="Lot fetched.",
    )


@staff_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Read staff catalog lots list with filters.",
    response_model=BaseHttpResponseModel[
        ListResponsesOnce[StaffLotListItemResponse]
    ],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[StaffLotListItemResponse]
            ],
            "description": "Staff lot list.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid lots list query params.",
        },
    },
)
async def get_staff_lots_route(
    query_model: GetStaffLotsQueryModel = Depends(get_staff_lots_query_model),
) -> BaseHttpResponseModel[ListResponsesOnce[StaffLotListItemResponse]]:
    lots = await query_model.get_items()
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[
                StaffLotListItemResponse.build(lot)
                for lot in lots
            ]
        ),
        message="Lots fetched.",
    )


@staff_router.get(
    "/by-slug/{game_slug}/{category_slug}/{lot_slug}",
    status_code=status.HTTP_200_OK,
    description="Read staff catalog lot by game/category/lot slugs.",
    response_model=BaseHttpResponseModel[LotDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotDetailResponse],
            "description": "Lot fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot not found.",
        },
    },
)
async def get_staff_lot_by_slug_route(
    game_slug: GameSlug = Path(),
    category_slug: CategorySlug = Path(),
    lot_slug: LotSlug = Path(),
) -> BaseHttpResponseModel[LotDetailResponse]:
    lot = await get_staff_lot_by_slugs(
        game_slug=game_slug,
        category_slug=category_slug,
        lot_slug=lot_slug,
    )
    return BaseHttpResponseModel(
        data=LotDetailResponse.build(
            lot,
            include_inactive_options=True,
        ),
        message="Lot fetched.",
    )


@staff_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    description="Create catalog lot.",
    response_model=BaseHttpResponseModel[LotCreatedResponse],
    responses={
        status.HTTP_201_CREATED: {
            "model": BaseHttpResponseModel[LotCreatedResponse],
            "description": "Lot created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid lot input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Category not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Lot slug conflict in category scope.",
        },
    },
)
async def create_lot_route(
    payload: CreateLotRequest,
) -> BaseHttpResponseModel[LotCreatedResponse]:
    lot = await create_lot(payload=payload)
    return BaseHttpResponseModel(
        data=LotCreatedResponse.build(lot.id),
        message="Lot created.",
    )


@staff_router.patch(
    "/{lot_id}",
    status_code=status.HTTP_200_OK,
    description="Patch catalog lot.",
    response_model=BaseHttpResponseModel[LotDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotDetailResponse],
            "description": "Lot updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid lot patch input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot or category not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Lot slug conflict in category scope.",
        },
    },
)
async def patch_lot_route(
    payload: PatchLotRequest,
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotDetailResponse]:
    lot = await patch_lot(lot_id=lot_id, payload=payload)
    return BaseHttpResponseModel(
        data=LotDetailResponse.build(
            lot,
            include_inactive_options=True,
        ),
        message="Lot updated.",
    )


@staff_router.delete(
    "/{lot_id}",
    status_code=status.HTTP_200_OK,
    description="Soft delete catalog lot.",
    dependencies=[Depends(require_catalog_soft_delete_access)],
    response_model=BaseHttpResponseModel[LotDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotDetailResponse],
            "description": "Lot soft-deleted.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponseModel,
            "description": "Not enough permissions.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot not found.",
        },
    },
)
async def soft_delete_lot_route(
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotDetailResponse]:
    lot = await soft_delete_lot(lot_id=lot_id)
    return BaseHttpResponseModel(
        data=LotDetailResponse.build(
            lot,
            include_inactive_options=True,
        ),
        message="Lot deleted.",
    )


@staff_router.post(
    "/{lot_id}/restore",
    status_code=status.HTTP_200_OK,
    description="Restore soft-deleted lot to INACTIVE status.",
    dependencies=[Depends(require_catalog_restore_access)],
    response_model=BaseHttpResponseModel[LotDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotDetailResponse],
            "description": "Lot restored.",
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
            "description": "Lot not found.",
        },
    },
)
async def restore_lot_route(
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotDetailResponse]:
    lot = await restore_lot(lot_id=lot_id)
    return BaseHttpResponseModel(
        data=LotDetailResponse.build(
            lot,
            include_inactive_options=True,
        ),
        message="Lot restored.",
    )


# ---------------------------
# ServicePage
# ---------------------------
@staff_router.put(
    "/{lot_id}/page",
    status_code=status.HTTP_200_OK,
    description="Create or update lot page draft.",
    response_model=BaseHttpResponseModel[LotPageResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotPageResponse],
            "description": "Lot page upserted.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid page input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot not found.",
        },
    },
)
async def upsert_lot_page_route(
    payload: UpsertLotPageRequest,
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotPageResponse]:
    page = await upsert_lot_page(
        lot_id=lot_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotPageResponse.build(page),
        message="Lot page upserted.",
    )


@staff_router.get(
    "/{lot_id}/page",
    status_code=status.HTTP_200_OK,
    description="Read lot page for backoffice editor.",
    response_model=BaseHttpResponseModel[LotPageResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotPageResponse],
            "description": "Lot page fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot page not found.",
        },
    },
)
async def get_lot_page_route(
    query_model: GetLotPageQueryModel = Depends(get_lot_page_query_model),
) -> BaseHttpResponseModel[LotPageResponse]:
    page = await query_model.get_item()
    return BaseHttpResponseModel(
        data=LotPageResponse.build(page),
        message="Lot page fetched.",
    )


@staff_router.patch(
    "/{lot_id}/page/status",
    status_code=status.HTTP_200_OK,
    description="Change lot page publication status.",
    response_model=BaseHttpResponseModel[LotPageResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotPageResponse],
            "description": "Lot page status updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid page status input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot page not found.",
        },
    },
)
async def change_lot_page_status_route(
    payload: ChangeLotPageStatusRequest,
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotPageResponse]:
    page = await change_lot_page_status(
        lot_id=lot_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotPageResponse.build(page),
        message="Lot page status updated.",
    )


# ---------------------------
# ServiceOption
# ---------------------------
@staff_router.get(
    "/{lot_id}/options",
    status_code=status.HTTP_200_OK,
    description="Read lot options for backoffice editor.",
    response_model=BaseHttpResponseModel[ListResponsesOnce[LotOptionResponse]],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[LotOptionResponse]
            ],
            "description": "Lot options fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot not found.",
        },
    },
)
async def get_lot_options_route(
    query_model: GetLotOptionsQueryModel = Depends(
        get_staff_lot_options_query_model
    ),
) -> BaseHttpResponseModel[ListResponsesOnce[LotOptionResponse]]:
    options = await query_model.get_items()
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[
                LotOptionResponse.build(
                    option,
                    include_inactive=True,
                )
                for option in options
            ]
        ),
        message="Lot options fetched.",
    )


@staff_router.get(
    "/{lot_id}/options/{option_id}",
    status_code=status.HTTP_200_OK,
    description="Read lot option for backoffice editor.",
    response_model=BaseHttpResponseModel[LotOptionResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotOptionResponse],
            "description": "Lot option fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot option not found.",
        },
    },
)
async def get_lot_option_route(
    query_model: GetLotOptionQueryModel = Depends(
        get_staff_lot_option_query_model
    ),
) -> BaseHttpResponseModel[LotOptionResponse]:
    option = await query_model.get_item()
    return BaseHttpResponseModel(
        data=LotOptionResponse.build(option, include_inactive=True),
        message="Lot option fetched.",
    )


@staff_router.post(
    "/{lot_id}/options",
    status_code=status.HTTP_201_CREATED,
    description="Create lot option.",
    response_model=BaseHttpResponseModel[LotOptionResponse],
    responses={
        status.HTTP_201_CREATED: {
            "model": BaseHttpResponseModel[LotOptionResponse],
            "description": "Lot option created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid option input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot or dependency not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Option code conflict in lot scope.",
        },
    },
)
async def create_lot_option_route(
    payload: CreateLotOptionRequest,
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotOptionResponse]:
    option = await create_lot_option(
        lot_id=lot_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotOptionResponse.build(option, include_inactive=True),
        message="Lot option created.",
    )


@staff_router.patch(
    "/{lot_id}/options/reorder",
    status_code=status.HTTP_200_OK,
    description="Reorder lot options in lot scope.",
    response_model=BaseHttpResponseModel[ListResponsesOnce[LotOptionResponse]],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[LotOptionResponse]
            ],
            "description": "Lot options reordered.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid lot options reorder payload.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot not found.",
        },
    },
)
async def reorder_lot_options_route(
    payload: ReorderLotOptionsRequest,
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[ListResponsesOnce[LotOptionResponse]]:
    options = await reorder_lot_options(
        lot_id=lot_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[
                LotOptionResponse.build(
                    option,
                    include_inactive=True,
                )
                for option in options
            ]
        ),
        message="Lot options reordered.",
    )


@staff_router.patch(
    "/{lot_id}/options/{option_id}",
    status_code=status.HTTP_200_OK,
    description=(
        "Update lot option fields. "
        "sort_order is not accepted in this PATCH; "
        "use PATCH /{lot_id}/options/reorder."
    ),
    response_model=BaseHttpResponseModel[LotOptionResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotOptionResponse],
            "description": "Lot option updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid option input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot or option not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Option code conflict in lot scope.",
        },
    },
)
async def update_lot_option_route(
    payload: UpdateLotOptionRequest,
    lot_id: IntId = Path(),
    option_id: IntId = Path(),
) -> BaseHttpResponseModel[LotOptionResponse]:
    option = await update_lot_option(
        lot_id=lot_id,
        option_id=option_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotOptionResponse.build(option, include_inactive=True),
        message="Lot option updated.",
    )


@staff_router.delete(
    "/{lot_id}/options/{option_id}",
    status_code=status.HTTP_200_OK,
    description="Delete lot option.",
    response_model=BaseHttpResponseModel[ListResponsesOnce[LotOptionResponse]],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[LotOptionResponse]
            ],
            "description": "Lot option deleted.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot option not found.",
        },
    },
)
async def delete_lot_option_route(
    lot_id: IntId = Path(),
    option_id: IntId = Path(),
) -> BaseHttpResponseModel[ListResponsesOnce[LotOptionResponse]]:
    options = await delete_lot_option(
        lot_id=lot_id,
        option_id=option_id,
    )
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[
                LotOptionResponse.build(
                    option,
                    include_inactive=True,
                )
                for option in options
            ]
        ),
        message="Lot option deleted.",
    )


# ---------------------------
# ServicePageBlock
# ---------------------------
@staff_router.post(
    "/{lot_id}/page/blocks",
    status_code=status.HTTP_200_OK,
    description="Create lot page block.",
    response_model=BaseHttpResponseModel[LotPageResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotPageResponse],
            "description": "Lot page block created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid block input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot page not found.",
        },
    },
)
async def create_lot_page_block_route(
    payload: CreateLotPageBlockRequest,
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotPageResponse]:
    page = await create_lot_page_block(
        lot_id=lot_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotPageResponse.build(page),
        message="Lot page block created.",
    )


@staff_router.patch(
    "/{lot_id}/page/blocks/reorder",
    status_code=status.HTTP_200_OK,
    description="Reorder lot page blocks in page scope.",
    response_model=BaseHttpResponseModel[LotPageResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotPageResponse],
            "description": "Lot page blocks reordered.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid lot page blocks reorder payload.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot page not found.",
        },
    },
)
async def reorder_lot_page_blocks_route(
    payload: ReorderLotPageBlocksRequest,
    lot_id: IntId = Path(),
) -> BaseHttpResponseModel[LotPageResponse]:
    page = await reorder_lot_page_blocks(
        lot_id=lot_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotPageResponse.build(page),
        message="Lot page blocks reordered.",
    )


@staff_router.patch(
    "/{lot_id}/page/blocks/{block_id}",
    status_code=status.HTTP_200_OK,
    description=(
        "Update lot page block payload. "
        "position is not accepted in this PATCH; "
        "use PATCH /{lot_id}/page/blocks/reorder."
    ),
    response_model=BaseHttpResponseModel[LotPageResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotPageResponse],
            "description": "Lot page block updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid block input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot page or block not found.",
        },
    },
)
async def update_lot_page_block_route(
    payload: UpdateLotPageBlockRequest,
    lot_id: IntId = Path(),
    block_id: IntId = Path(),
) -> BaseHttpResponseModel[LotPageResponse]:
    page = await update_lot_page_block(
        lot_id=lot_id,
        block_id=block_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotPageResponse.build(page),
        message="Lot page block updated.",
    )


@staff_router.delete(
    "/{lot_id}/page/blocks/{block_id}",
    status_code=status.HTTP_200_OK,
    description="Delete lot page block.",
    response_model=BaseHttpResponseModel[LotPageResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotPageResponse],
            "description": "Lot page block deleted.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot page or block not found.",
        },
    },
)
async def delete_lot_page_block_route(
    lot_id: IntId = Path(),
    block_id: IntId = Path(),
) -> BaseHttpResponseModel[LotPageResponse]:
    page = await delete_lot_page_block(
        lot_id=lot_id,
        block_id=block_id,
    )
    return BaseHttpResponseModel(
        data=LotPageResponse.build(page),
        message="Lot page block deleted.",
    )


# ---------------------------
# ServiceOptionValue
# ---------------------------
@staff_router.post(
    "/{lot_id}/options/{option_id}/values",
    status_code=status.HTTP_201_CREATED,
    description="Create lot option value.",
    response_model=BaseHttpResponseModel[LotOptionResponse],
    responses={
        status.HTTP_201_CREATED: {
            "model": BaseHttpResponseModel[LotOptionResponse],
            "description": "Lot option value created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid option value input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot or option not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Option value code conflict in option scope.",
        },
    },
)
async def create_lot_option_value_route(
    payload: CreateLotOptionValueRequest,
    lot_id: IntId = Path(),
    option_id: IntId = Path(),
) -> BaseHttpResponseModel[LotOptionResponse]:
    option = await create_lot_option_value(
        lot_id=lot_id,
        option_id=option_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotOptionResponse.build(option, include_inactive=True),
        message="Lot option value created.",
    )


@staff_router.patch(
    "/{lot_id}/options/{option_id}/values/reorder",
    status_code=status.HTTP_200_OK,
    description="Reorder lot option values in option scope.",
    response_model=BaseHttpResponseModel[LotOptionResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotOptionResponse],
            "description": "Lot option values reordered.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid lot option values reorder payload.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot or option not found.",
        },
    },
)
async def reorder_lot_option_values_route(
    payload: ReorderLotOptionValuesRequest,
    lot_id: IntId = Path(),
    option_id: IntId = Path(),
) -> BaseHttpResponseModel[LotOptionResponse]:
    option = await reorder_lot_option_values(
        lot_id=lot_id,
        option_id=option_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotOptionResponse.build(option, include_inactive=True),
        message="Lot option values reordered.",
    )


@staff_router.patch(
    "/{lot_id}/options/{option_id}/values/{value_id}",
    status_code=status.HTTP_200_OK,
    description=(
        "Update lot option value fields. "
        "sort_order is not accepted in this PATCH; "
        "use PATCH /{lot_id}/options/{option_id}/values/reorder."
    ),
    response_model=BaseHttpResponseModel[LotOptionResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotOptionResponse],
            "description": "Lot option value updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid option value input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot, option, or value not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Option value code conflict in option scope.",
        },
    },
)
async def update_lot_option_value_route(
    payload: UpdateLotOptionValueRequest,
    lot_id: IntId = Path(),
    option_id: IntId = Path(),
    value_id: IntId = Path(),
) -> BaseHttpResponseModel[LotOptionResponse]:
    option = await update_lot_option_value(
        lot_id=lot_id,
        option_id=option_id,
        value_id=value_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=LotOptionResponse.build(option, include_inactive=True),
        message="Lot option value updated.",
    )


@staff_router.delete(
    "/{lot_id}/options/{option_id}/values/{value_id}",
    status_code=status.HTTP_200_OK,
    description="Delete lot option value.",
    response_model=BaseHttpResponseModel[LotOptionResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[LotOptionResponse],
            "description": "Lot option value deleted.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot, option, or value not found.",
        },
    },
)
async def delete_lot_option_value_route(
    lot_id: IntId = Path(),
    option_id: IntId = Path(),
    value_id: IntId = Path(),
) -> BaseHttpResponseModel[LotOptionResponse]:
    option = await delete_lot_option_value(
        lot_id=lot_id,
        option_id=option_id,
        value_id=value_id,
    )
    return BaseHttpResponseModel(
        data=LotOptionResponse.build(option, include_inactive=True),
        message="Lot option value deleted.",
    )
