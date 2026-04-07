from fastapi import APIRouter, Depends, Path
from starlette import status

from wow_shop.api.responses import ErrorResponseModel
from wow_shop.shared.contracts import (
    BaseHttpResponseModel,
    ListResponses,
    ListResponsesOnce,
)
from wow_shop.shared.types import IntId
from wow_shop.modules.pricing.api.query.promotions_query import (
    GetPublicPromotionsContextQueryModel,
    get_public_promotions_context_query_model,
)
from wow_shop.modules.pricing.api.query.staff_promotions_query import (
    GetStaffPromotionsQueryModel,
    get_staff_promotions_query_model,
)
from wow_shop.modules.pricing.api.query.staff_promotion_assignments_query import (
    GetStaffPromotionAssignmentsQueryModel,
    get_staff_promotion_assignments_query_model,
)
from wow_shop.modules.pricing.api.request.models import (
    CreatePromotionAssignmentRequest,
    CreatePromotionRequest,
    PatchPromotionRequest,
)
from wow_shop.modules.pricing.api.response.models import (
    PublicPromotionContextItemResponse,
    PromotionAssignmentResponse,
    AssignmentDetailResponse,
    PromotionCreatedResponse,
    PromotionDetailResponse,
    PromotionListItemResponse,
    PromotionListMetaResponse,
    PromotionAssignmentListMetaResponse,
)
from wow_shop.modules.pricing.application.pricing_commands import (
    create_promotion_assignment,
    create_promotion,
    delete_promotion_assignment,
    patch_promotion,
)
from wow_shop.modules.pricing.application.pricing_service import (
    get_staff_promotion_by_id,
)

public_router = APIRouter(tags=["pricing"])
staff_router = APIRouter(prefix="/promotions", tags=["promotions"])


@public_router.get(
    "/promotions",
    status_code=status.HTTP_200_OK,
    description=(
        "Read storefront promotions context for requested lot/category scope. "
        "Supports badge-discovery and explicit scope filter: LOT, CATEGORY, or ALL."
    ),
    response_model=BaseHttpResponseModel[
        ListResponsesOnce[PublicPromotionContextItemResponse]
    ],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponsesOnce[PublicPromotionContextItemResponse]
            ],
            "description": "Promotions fetched.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "At least one promotions context filter is required.",
        },
    },
)
async def get_public_promotions_context_route(
    query_model: GetPublicPromotionsContextQueryModel = Depends(
        get_public_promotions_context_query_model
    ),
) -> BaseHttpResponseModel[ListResponsesOnce[PublicPromotionContextItemResponse]]:
    items = await query_model.get_items()
    return BaseHttpResponseModel(
        data=ListResponsesOnce.from_items(
            items=[
                PublicPromotionContextItemResponse.build(item)
                for item in items
            ]
        ),
        message="Promotions fetched.",
    )


@staff_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Read staff promotions list.",
    response_model=BaseHttpResponseModel[
        ListResponses[PromotionListItemResponse, PromotionListMetaResponse]
    ],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponses[
                    PromotionListItemResponse,
                    PromotionListMetaResponse,
                ]
            ],
            "description": "Promotions list fetched.",
        },
    },
)
async def get_staff_promotions_route(
    query_model: GetStaffPromotionsQueryModel = Depends(
        get_staff_promotions_query_model
    ),
) -> BaseHttpResponseModel[
    ListResponses[PromotionListItemResponse, PromotionListMetaResponse]
]:
    result = await query_model.get_items()
    return BaseHttpResponseModel(
        data=ListResponses.with_meta(
            items=[
                PromotionListItemResponse.build(promotion)
                for promotion in result.items
            ],
            meta=PromotionListMetaResponse.build(
                limit=result.limit,
                offset=result.offset,
                total=result.total,
            ),
        ),
        message="Promotions fetched.",
    )


@staff_router.get(
    "/{promotion_id}",
    status_code=status.HTTP_200_OK,
    description="Read staff promotion detail by id.",
    response_model=BaseHttpResponseModel[PromotionDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[PromotionDetailResponse],
            "description": "Promotion fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Promotion not found.",
        },
    },
)
async def get_staff_promotion_by_id_route(
    promotion_id: IntId = Path(),
) -> BaseHttpResponseModel[PromotionDetailResponse]:
    promotion = await get_staff_promotion_by_id(promotion_id=promotion_id)
    return BaseHttpResponseModel(
        data=PromotionDetailResponse.build(promotion),
        message="Promotion fetched.",
    )


@staff_router.get(
    "/{promotion_id}/assignments",
    status_code=status.HTTP_200_OK,
    description="Read staff promotion assignments list by promotion id.",
    response_model=BaseHttpResponseModel[
        ListResponses[
            PromotionAssignmentResponse,
            PromotionAssignmentListMetaResponse,
        ]
    ],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[
                ListResponses[
                    PromotionAssignmentResponse,
                    PromotionAssignmentListMetaResponse,
                ]
            ],
            "description": "Promotion assignments fetched.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Promotion not found.",
        },
    },
)
async def get_staff_promotion_assignments_route(
    query_model: GetStaffPromotionAssignmentsQueryModel = Depends(
        get_staff_promotion_assignments_query_model
    ),
) -> BaseHttpResponseModel[
    ListResponses[
        PromotionAssignmentResponse,
        PromotionAssignmentListMetaResponse,
    ]
]:
    result = await query_model.get_items()
    return BaseHttpResponseModel(
        data=ListResponses.with_meta(
            items=[
                PromotionAssignmentResponse.build(assignment)
                for assignment in result.items
            ],
            meta=PromotionAssignmentListMetaResponse.build(
                limit=result.limit,
                offset=result.offset,
                total=result.total,
            ),
        ),
        message="Promotion assignments fetched.",
    )


@staff_router.post(
    "/{promotion_id}/assignments",
    status_code=status.HTTP_201_CREATED,
    description="Create promotion assignment.",
    response_model=BaseHttpResponseModel[AssignmentDetailResponse],
    responses={
        status.HTTP_201_CREATED: {
            "model": BaseHttpResponseModel[AssignmentDetailResponse],
            "description": "Promotion assignment created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid promotion assignment input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Promotion or user not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Promotion assignment for user already exists.",
        },
    },
)
async def create_promotion_assignment_route(
    payload: CreatePromotionAssignmentRequest,
    promotion_id: IntId = Path(),
) -> BaseHttpResponseModel[AssignmentDetailResponse]:
    assignment = await create_promotion_assignment(
        promotion_id=promotion_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=AssignmentDetailResponse.build(assignment),
        message="Promotion assignment created.",
    )


@staff_router.delete(
    "/{promotion_id}/assignments/{assignment_id}",
    status_code=status.HTTP_200_OK,
    description="Delete promotion assignment.",
    response_model=BaseHttpResponseModel[AssignmentDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[AssignmentDetailResponse],
            "description": "Promotion assignment deleted.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Cannot delete last assignment for personal promotion.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Promotion or assignment not found.",
        },
    },
)
async def delete_promotion_assignment_route(
    promotion_id: IntId = Path(),
    assignment_id: IntId = Path(),
) -> BaseHttpResponseModel[AssignmentDetailResponse]:
    assignment = await delete_promotion_assignment(
        promotion_id=promotion_id,
        assignment_id=assignment_id,
    )
    return BaseHttpResponseModel(
        data=AssignmentDetailResponse.build(assignment),
        message="Promotion assignment deleted.",
    )


@staff_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    description="Create promotion.",
    response_model=BaseHttpResponseModel[PromotionCreatedResponse],
    responses={
        status.HTTP_201_CREATED: {
            "model": BaseHttpResponseModel[PromotionCreatedResponse],
            "description": "Promotion created.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid promotion input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Lot, category, or user not found.",
        },
    },
)
async def create_promotion_route(
    payload: CreatePromotionRequest,
) -> BaseHttpResponseModel[PromotionCreatedResponse]:
    promotion = await create_promotion(payload=payload)
    return BaseHttpResponseModel(
        data=PromotionCreatedResponse.build(promotion.id),
        message="Promotion created.",
    )


@staff_router.patch(
    "/{promotion_id}",
    status_code=status.HTTP_200_OK,
    description="Patch promotion.",
    response_model=BaseHttpResponseModel[PromotionDetailResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[PromotionDetailResponse],
            "description": "Promotion updated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid promotion patch input.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponseModel,
            "description": "Promotion not found.",
        },
    },
)
async def patch_promotion_route(
    payload: PatchPromotionRequest,
    promotion_id: IntId = Path(),
) -> BaseHttpResponseModel[PromotionDetailResponse]:
    promotion = await patch_promotion(
        promotion_id=promotion_id,
        payload=payload,
    )
    return BaseHttpResponseModel(
        data=PromotionDetailResponse.build(promotion),
        message="Promotion updated.",
    )
