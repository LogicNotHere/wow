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
from wow_shop.modules.catalog.infrastructure.db.models import Game, GameStatus
from wow_shop.shared.auth.context import get_auth_user_role
from wow_shop.shared.contracts import BaseRequestModel


class GameListStatusParam(StrEnum):
    ALL = "all"


class GetGamesQueryModel(BaseRequestModel):
    status: GameStatus | Literal["all"] | None = None
    role: UserRole | None = None

    @staticmethod
    def _allowed_statuses_for_role(role: UserRole | None) -> tuple[GameStatus, ...]:
        if role in {UserRole.ADMIN, UserRole.MANAGER}:
            return (
                GameStatus.DRAFT,
                GameStatus.ACTIVE,
                GameStatus.INACTIVE,
                GameStatus.DELETED,
            )
        if role == UserRole.OPERATOR:
            return (
                GameStatus.ACTIVE,
                GameStatus.INACTIVE,
                GameStatus.DELETED,
            )
        if role == UserRole.CONTENT_MANAGER:
            return (
                GameStatus.DRAFT,
                GameStatus.ACTIVE,
                GameStatus.DELETED,
            )
        return (GameStatus.ACTIVE,)

    @property
    def _is_staff_request(self) -> bool:
        return self.role in {
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.OPERATOR,
            UserRole.CONTENT_MANAGER,
        }

    def _status_label(self) -> str:
        if isinstance(self.status, GameStatus):
            return self.status.value
        return str(self.status)

    def _resolve_status_filter(self) -> tuple[GameStatus, ...]:
        allowed_statuses = self._allowed_statuses_for_role(self.role)

        if self.status is None:
            return allowed_statuses

        if not self._is_staff_request and (
            self.status == GameListStatusParam.ALL
            or (
                isinstance(self.status, GameStatus)
                and self.status != GameStatus.ACTIVE
            )
        ):
            ensure_catalog_deleted_view_access(self.role)

        if self.status == GameListStatusParam.ALL:
            return allowed_statuses

        if self.status not in allowed_statuses:
            raise CatalogValidationError(
                f"Status '{self._status_label()}' is not allowed for current access context."
            )

        return (self.status,)

    def build_query(self) -> Select[tuple[Game]]:
        query = select(Game)
        resolved_statuses = self._resolve_status_filter()
        query = query.where(Game.status.in_(resolved_statuses))
        return query.order_by(
            Game.sort_order.asc(),
            Game.id.asc(),
        )

    async def get_items(self) -> list[Game]:
        result = await s.db.execute(self.build_query())
        return list(result.scalars().all())


def get_games_query_model(
    status: GameStatus | Literal["all"] | None = Query(
        default=None,
        description=(
            "Game status filter. Public supports only `active`. "
            "Staff supports role-based subset of "
            "`draft|active|inactive|deleted|all`."
        ),
    ),
) -> GetGamesQueryModel:
    role = get_auth_user_role()
    return GetGamesQueryModel(
        status=status,
        role=role,
    )
