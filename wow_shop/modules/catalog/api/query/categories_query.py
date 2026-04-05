from __future__ import annotations

from enum import StrEnum
from typing import Literal

from fastapi import Query
from sqlalchemy import select
from sqlalchemy.sql import Select

from wow_shop.infrastructure.db.session import s
from wow_shop.api.dependencies.permissions import (
    ensure_catalog_deleted_view_access,
)
from wow_shop.modules.auth.infrastructure.db.models import UserRole
from wow_shop.modules.catalog.application.errors import CatalogValidationError
from wow_shop.modules.catalog.application.category_service import (
    apply_public_category_visibility,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    ServiceCategory,
    ServiceCategoryStatus,
)
from wow_shop.shared.auth.context import get_auth_user_role
from wow_shop.shared.contracts import BaseRequestModel
from wow_shop.shared.types import IntId


class CategoryListStatusParam(StrEnum):
    ALL = "all"


class GetCategoriesQueryModel(BaseRequestModel):
    game_id: IntId | None = None
    status: ServiceCategoryStatus | Literal["all"] | None = None
    role: UserRole | None = None

    @staticmethod
    def _allowed_statuses_for_role(
        role: UserRole | None,
    ) -> tuple[ServiceCategoryStatus, ...]:
        if role in {UserRole.ADMIN, UserRole.MANAGER}:
            return (
                ServiceCategoryStatus.DRAFT,
                ServiceCategoryStatus.ACTIVE,
                ServiceCategoryStatus.INACTIVE,
                ServiceCategoryStatus.DELETED,
            )
        if role == UserRole.OPERATOR:
            return (
                ServiceCategoryStatus.ACTIVE,
                ServiceCategoryStatus.INACTIVE,
                ServiceCategoryStatus.DELETED,
            )
        if role == UserRole.CONTENT_MANAGER:
            return (
                ServiceCategoryStatus.DRAFT,
                ServiceCategoryStatus.ACTIVE,
                ServiceCategoryStatus.DELETED,
            )
        return (ServiceCategoryStatus.ACTIVE,)

    @property
    def _is_staff_request(self) -> bool:
        return self.role in {
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.OPERATOR,
            UserRole.CONTENT_MANAGER,
        }

    def _status_label(self) -> str:
        if isinstance(self.status, ServiceCategoryStatus):
            return self.status.value
        return str(self.status)

    def _resolve_status_filter(self) -> tuple[ServiceCategoryStatus, ...]:
        allowed_statuses = self._allowed_statuses_for_role(self.role)

        if self.status is None:
            return allowed_statuses

        if not self._is_staff_request and (
            self.status == CategoryListStatusParam.ALL
            or (
                isinstance(self.status, ServiceCategoryStatus)
                and self.status != ServiceCategoryStatus.ACTIVE
            )
        ):
            ensure_catalog_deleted_view_access(self.role)

        if self.status == CategoryListStatusParam.ALL:
            return allowed_statuses

        if self.status not in allowed_statuses:
            raise CatalogValidationError(
                f"Status '{self._status_label()}' is not allowed for current access context."
            )

        return (self.status,)

    def build_query(self) -> Select[tuple[ServiceCategory]]:
        query = select(ServiceCategory).join(ServiceCategory.game)
        if self.game_id is not None:
            query = query.where(ServiceCategory.game_id == self.game_id)
        query = query.where(
            ServiceCategory.status.in_(self._resolve_status_filter())
        )
        if not self._is_staff_request:
            query = query.where(Game.status == GameStatus.ACTIVE)
            query = apply_public_category_visibility(query)

        return query.order_by(
            ServiceCategory.game_id.asc(),
            ServiceCategory.sort_order.asc(),
            ServiceCategory.id.asc(),
        )

    async def get_items(self) -> list[ServiceCategory]:
        result = await s.db.execute(self.build_query())
        return list(result.scalars().all())


def get_categories_query_model(
    game_id: IntId | None = Query(default=None),
    status: ServiceCategoryStatus | Literal["all"] | None = Query(
        default=None,
        description=(
            "Category status filter. Public supports only `active`. "
            "Staff supports role-based subset of "
            "`draft|active|inactive|deleted|all`."
        ),
    ),
) -> GetCategoriesQueryModel:
    role = get_auth_user_role()
    return GetCategoriesQueryModel(
        game_id=game_id,
        status=status,
        role=role,
    )
