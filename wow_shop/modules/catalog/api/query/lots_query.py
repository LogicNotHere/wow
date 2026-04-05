from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select

from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    CategoryNotFoundError,
    GameNotFoundError,
    LotNotFoundError,
    LotOptionNotFoundError,
    LotPageNotFoundError,
)
from wow_shop.modules.catalog.application.read_utils import (
    apply_public_lot_visibility,
)
from wow_shop.modules.catalog.application.category_service import (
    apply_public_category_visibility,
)
from wow_shop.modules.catalog.api.query.lots_filters import (
    StaffLotsFilters,
    get_staff_lots_filters,
)
from wow_shop.modules.catalog.api.request.category_models import CategorySlug
from wow_shop.modules.catalog.api.request.game_models import GameSlug
from wow_shop.modules.catalog.application.query_filters import apply_filters
from wow_shop.modules.catalog.constants import (
    CATEGORY_SLUG_PATTERN,
    GAME_SLUG_PATTERN,
)
from wow_shop.infrastructure.db.session import s
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    LotOption,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServicePage,
)
from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.types import IntId


class StaffLotsOrderByParam(StrEnum):
    CREATED_AT_DESC = "created_at_desc"
    CREATED_AT_ASC = "created_at_asc"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    STATUS_ASC = "status_asc"
    STATUS_DESC = "status_desc"


class GetStaffLotsQueryModel(BaseRequestModel):
    filters: StaffLotsFilters
    limit: int = 50
    offset: int = 0
    order_by: StaffLotsOrderByParam = StaffLotsOrderByParam.CREATED_AT_DESC

    def _resolve_order_by(self) -> tuple[object, object]:
        if self.order_by == StaffLotsOrderByParam.CREATED_AT_ASC:
            return (
                ServiceLot.created_at.asc(),
                ServiceLot.id.asc(),
            )
        if self.order_by == StaffLotsOrderByParam.NAME_ASC:
            return (
                ServiceLot.name.asc(),
                ServiceLot.id.asc(),
            )
        if self.order_by == StaffLotsOrderByParam.NAME_DESC:
            return (
                ServiceLot.name.desc(),
                ServiceLot.id.desc(),
            )
        if self.order_by == StaffLotsOrderByParam.STATUS_ASC:
            return (
                ServiceLot.status.asc(),
                ServiceLot.id.asc(),
            )
        if self.order_by == StaffLotsOrderByParam.STATUS_DESC:
            return (
                ServiceLot.status.desc(),
                ServiceLot.id.desc(),
            )
        return (
            ServiceLot.created_at.desc(),
            ServiceLot.id.desc(),
        )

    def build_query(self) -> Select[tuple[ServiceLot]]:
        query = (
            select(ServiceLot)
            .join(ServiceLot.category)
            .join(ServiceCategory.game)
            .options(joinedload(ServiceLot.category))
        )
        query = apply_filters(
            query,
            filters=self.filters.to_query_filters(),
        )
        query = query.order_by(*self._resolve_order_by())
        return query.limit(self.limit).offset(self.offset)

    async def get_items(self) -> list[ServiceLot]:
        result = await s.db.execute(self.build_query())
        return list(result.scalars().all())


class GetPublicLotsQueryModel(BaseRequestModel):
    game_slug: str
    category_slug: str

    @staticmethod
    def _normalize_slug(
        value: str,
        *,
        field_label: str,
        pattern: object,
    ) -> str:
        normalized_value = value.strip().lower()
        if not normalized_value:
            raise CatalogValidationError(f"{field_label} is required.")
        if not pattern.fullmatch(normalized_value):
            raise CatalogValidationError(
                f"{field_label} must contain lowercase letters, digits, "
                "hyphens, or underscores."
            )
        return normalized_value

    async def _resolve_scope_category_id(self) -> int:
        normalized_game_slug = self._normalize_slug(
            self.game_slug,
            field_label="Game slug",
            pattern=GAME_SLUG_PATTERN,
        )
        normalized_category_slug = self._normalize_slug(
            self.category_slug,
            field_label="Category slug",
            pattern=CATEGORY_SLUG_PATTERN,
        )

        game_id_query = (
            select(Game.id)
            .where(
                Game.slug == normalized_game_slug,
                Game.status == GameStatus.ACTIVE,
            )
            .limit(1)
        )
        game_result = await s.db.execute(game_id_query)
        game_id = game_result.scalar_one_or_none()
        if game_id is None:
            raise GameNotFoundError("Game not found.")

        category_id_query = apply_public_category_visibility(
            select(ServiceCategory.id)
            .join(ServiceCategory.game)
            .where(
                ServiceCategory.game_id == game_id,
                ServiceCategory.slug == normalized_category_slug,
                ServiceCategory.status == ServiceCategoryStatus.ACTIVE,
            )
        )
        category_id_query = category_id_query.limit(1)
        category_result = await s.db.execute(category_id_query)
        category_id = category_result.scalar_one_or_none()
        if category_id is None:
            raise CategoryNotFoundError("Category not found.")
        return category_id

    def build_query(self, *, category_id: int) -> Select[tuple[ServiceLot]]:
        query = (
            select(ServiceLot)
            .join(ServiceLot.category)
            .join(ServiceCategory.game)
            .join(ServiceLot.page)
            .options(joinedload(ServiceLot.category))
            .where(ServiceLot.category_id == category_id)
        )
        query = apply_public_lot_visibility(query)
        return query.order_by(
            ServiceLot.id.asc(),
        )

    async def get_items(self) -> list[ServiceLot]:
        category_id = await self._resolve_scope_category_id()
        result = await s.db.execute(self.build_query(category_id=category_id))
        return list(result.scalars().all())


class GetLotPageQueryModel(BaseRequestModel):
    lot_id: IntId

    def build_query(self) -> Select[tuple[ServicePage]]:
        return (
            select(ServicePage)
            .options(selectinload(ServicePage.blocks))
            .where(ServicePage.lot_id == self.lot_id)
        )

    async def get_item(self) -> ServicePage:
        result = await s.db.execute(self.build_query())
        item = result.scalar_one_or_none()
        if item is None:
            raise LotPageNotFoundError("Lot page not found.")
        return item


class GetLotOptionsQueryModel(BaseRequestModel):
    lot_id: IntId
    include_inactive: bool = True

    async def _ensure_lot_exists(self) -> None:
        query = select(ServiceLot.id).where(ServiceLot.id == self.lot_id).limit(1)
        result = await s.db.execute(query)
        if result.scalar_one_or_none() is None:
            raise LotNotFoundError("Lot not found.")

    def build_query(self) -> Select[tuple[LotOption]]:
        query = (
            select(LotOption)
            .options(selectinload(LotOption.values))
            .where(LotOption.lot_id == self.lot_id)
        )
        if not self.include_inactive:
            query = query.where(LotOption.is_active.is_(True))
        return query.order_by(
            LotOption.sort_order.asc(),
            LotOption.id.asc(),
        )

    async def get_items(self) -> list[LotOption]:
        await self._ensure_lot_exists()
        result = await s.db.execute(self.build_query())
        return list(result.scalars().all())


class GetLotOptionQueryModel(BaseRequestModel):
    lot_id: IntId
    option_id: IntId

    def build_query(self) -> Select[tuple[LotOption]]:
        return (
            select(LotOption)
            .options(selectinload(LotOption.values))
            .where(
                LotOption.id == self.option_id,
                LotOption.lot_id == self.lot_id,
            )
        )

    async def get_item(self) -> LotOption:
        result = await s.db.execute(self.build_query())
        item = result.scalar_one_or_none()
        if item is None:
            raise LotOptionNotFoundError("Lot option not found.")
        return item


def get_staff_lots_query_model(
    filters: StaffLotsFilters = Depends(get_staff_lots_filters),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order_by: StaffLotsOrderByParam = Query(
        default=StaffLotsOrderByParam.CREATED_AT_DESC
    ),
) -> GetStaffLotsQueryModel:
    return GetStaffLotsQueryModel(
        filters=filters,
        limit=limit,
        offset=offset,
        order_by=order_by,
    )


def get_public_lots_query_model(
    game_slug: GameSlug = Path(),
    category_slug: CategorySlug = Path(),
) -> GetPublicLotsQueryModel:
    return GetPublicLotsQueryModel(
        game_slug=game_slug,
        category_slug=category_slug,
    )


def get_lot_page_query_model(
    lot_id: IntId = Path(),
) -> GetLotPageQueryModel:
    return GetLotPageQueryModel(lot_id=lot_id)


def get_staff_lot_options_query_model(
    lot_id: IntId = Path(),
) -> GetLotOptionsQueryModel:
    return GetLotOptionsQueryModel(
        lot_id=lot_id,
        include_inactive=True,
    )


def get_staff_lot_option_query_model(
    lot_id: IntId = Path(),
    option_id: IntId = Path(),
) -> GetLotOptionQueryModel:
    return GetLotOptionQueryModel(
        lot_id=lot_id,
        option_id=option_id,
    )
