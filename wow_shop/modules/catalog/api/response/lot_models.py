from __future__ import annotations

from datetime import datetime
from typing import Self

from wow_shop.shared.contracts import BaseResponseDataModel
from wow_shop.modules.catalog.infrastructure.db.models import (
    LotOption,
    LotOptionInputType,
    LotOptionValue,
    ServiceLot,
    ServiceLotStatus,
    ServicePage,
    ServicePageBlock,
    ServicePageStatus,
)


class LotCreatedResponse(BaseResponseDataModel):
    id: int

    @classmethod
    def build(cls, lot_id: int) -> Self:
        return cls(id=lot_id)


class LotListItemResponse(BaseResponseDataModel):
    id: int
    game_id: int
    category_id: int
    name: str
    slug: str
    description: str | None
    status: ServiceLotStatus
    base_price_eur: float

    @classmethod
    def build(cls, lot: ServiceLot) -> Self:
        return cls(
            id=lot.id,
            game_id=lot.category.game_id,
            category_id=lot.category_id,
            name=lot.name,
            slug=lot.slug,
            description=lot.description,
            status=lot.status,
            base_price_eur=lot.base_price_eur,
        )


class StaffLotListItemResponse(BaseResponseDataModel):
    id: int
    game_id: int
    category_id: int
    name: str
    slug: str
    description: str | None
    status: ServiceLotStatus
    base_price_eur: float

    @classmethod
    def build(cls, lot: ServiceLot) -> Self:
        return cls(
            id=lot.id,
            game_id=lot.category.game_id,
            category_id=lot.category_id,
            name=lot.name,
            slug=lot.slug,
            description=lot.description,
            status=lot.status,
            base_price_eur=lot.base_price_eur,
        )


class LotOptionValueResponse(BaseResponseDataModel):
    id: int
    label: str
    code: str
    description: str | None
    price_value: float
    sort_order: int
    is_default: bool
    is_active: bool

    @classmethod
    def build(cls, value: LotOptionValue) -> Self:
        return cls(
            id=value.id,
            label=value.label,
            code=value.code,
            description=value.description,
            price_value=value.price_value,
            sort_order=value.sort_order,
            is_default=value.is_default,
            is_active=value.is_active,
        )


class LotOptionResponse(BaseResponseDataModel):
    id: int
    label: str
    code: str
    input_type: LotOptionInputType
    is_required: bool
    sort_order: int
    is_active: bool
    depends_on_option_id: int | None
    depends_on_value_id: int | None
    values: list[LotOptionValueResponse]

    @classmethod
    def build(
        cls,
        option: LotOption,
        *,
        include_inactive: bool = False,
    ) -> Self:
        option_values = (
            option.values
            if include_inactive
            else [
                value
                for value in option.values
                if value.is_active
            ]
        )
        sorted_values = sorted(
            option_values,
            key=lambda value: (value.sort_order, value.id),
        )
        return cls(
            id=option.id,
            label=option.label,
            code=option.code,
            input_type=option.input_type,
            is_required=option.is_required,
            sort_order=option.sort_order,
            is_active=option.is_active,
            depends_on_option_id=option.depends_on_option_id,
            depends_on_value_id=option.depends_on_value_id,
            values=[
                LotOptionValueResponse.build(value)
                for value in sorted_values
            ],
        )


class LotPageBlockResponse(BaseResponseDataModel):
    id: int
    position: int
    type: str
    payload_json: dict | None

    @classmethod
    def build(cls, block: ServicePageBlock) -> Self:
        return cls(
            id=block.id,
            position=block.position,
            type=block.type,
            payload_json=block.payload_json,
        )


class LotPageResponse(BaseResponseDataModel):
    id: int
    lot_id: int
    status: ServicePageStatus
    title: str | None
    meta_json: dict | None
    published_at: datetime | None
    blocks: list[LotPageBlockResponse]

    @classmethod
    def build(cls, page: ServicePage) -> Self:
        sorted_blocks = sorted(
            page.blocks,
            key=lambda block: (block.position, block.id),
        )
        return cls(
            id=page.id,
            lot_id=page.lot_id,
            status=page.status,
            title=page.title,
            meta_json=page.meta_json,
            published_at=page.published_at,
            blocks=[
                LotPageBlockResponse.build(block) for block in sorted_blocks
            ],
        )


class LotDetailResponse(BaseResponseDataModel):
    id: int
    game_id: int
    category_id: int
    name: str
    slug: str
    description: str | None
    status: ServiceLotStatus
    base_price_eur: float
    options: list[LotOptionResponse]
    page: LotPageResponse | None

    @classmethod
    def build(
        cls,
        lot: ServiceLot,
        *,
        include_inactive_options: bool = False,
    ) -> Self:
        lot_options = (
            lot.options
            if include_inactive_options
            else [
                option
                for option in lot.options
                if option.is_active
            ]
        )
        sorted_options = sorted(
            lot_options,
            key=lambda option: (option.sort_order, option.id),
        )
        page = lot.page
        page_response = (
            LotPageResponse.build(page) if page is not None else None
        )
        return cls(
            id=lot.id,
            game_id=lot.category.game_id,
            category_id=lot.category_id,
            name=lot.name,
            slug=lot.slug,
            description=lot.description,
            status=lot.status,
            base_price_eur=lot.base_price_eur,
            options=[
                LotOptionResponse.build(
                    option,
                    include_inactive=include_inactive_options,
                )
                for option in sorted_options
            ],
            page=page_response,
        )
