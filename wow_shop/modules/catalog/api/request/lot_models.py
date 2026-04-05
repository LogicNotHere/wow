from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.pydantic import PartialModel
from wow_shop.shared.types import IntId
from wow_shop.modules.catalog.infrastructure.db.models import (
    LotOptionInputType,
    ServiceLotStatus,
    ServicePageStatus,
)

LotName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]
LotSlug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class LotCommonRequest(BaseRequestModel):
    category_id: IntId
    name: LotName
    slug: LotSlug
    description: str | None = None
    status: ServiceLotStatus = ServiceLotStatus.ACTIVE
    base_price_eur: float = Field(default=0, ge=0)


class CreateLotRequest(LotCommonRequest):
    pass


@PartialModel()
class PatchLotRequest(LotCommonRequest):
    pass


LotPageTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=255,
    ),
]


class UpsertLotPageRequest(BaseRequestModel):
    title: LotPageTitle | None = None
    meta_json: dict | None = None


class ChangeLotPageStatusRequest(BaseRequestModel):
    status: ServicePageStatus


BlockType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=50,
    ),
]


class CreateLotPageBlockRequest(BaseRequestModel):
    type: BlockType
    payload_json: dict | None = None
    position: int | None = Field(default=None, ge=0)


@PartialModel(exclude_fields={"type", "position"})
class UpdateLotPageBlockRequest(CreateLotPageBlockRequest):
    pass


OptionLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]
OptionCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]


class CreateLotOptionRequest(BaseRequestModel):
    label: OptionLabel
    code: OptionCode
    input_type: LotOptionInputType
    is_required: bool = False
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True
    depends_on_option_id: IntId | None = None
    depends_on_value_id: IntId | None = None


@PartialModel(exclude_fields={"sort_order"})
class UpdateLotOptionRequest(CreateLotOptionRequest):
    pass


class CreateLotOptionValueRequest(BaseRequestModel):
    label: OptionLabel
    code: OptionCode
    description: str | None = None
    price_value: float = Field(default=0, ge=0)
    sort_order: int = Field(default=0, ge=0)
    is_default: bool = False
    is_active: bool = True


@PartialModel(exclude_fields={"sort_order"})
class UpdateLotOptionValueRequest(CreateLotOptionValueRequest):
    pass


class ReorderIdsRequest(BaseRequestModel):
    ids: list[IntId]


class ReorderLotOptionsRequest(ReorderIdsRequest):
    pass


class ReorderLotOptionValuesRequest(ReorderIdsRequest):
    pass


class ReorderLotPageBlocksRequest(ReorderIdsRequest):
    pass
