from __future__ import annotations

from typing import Annotated
from collections.abc import Iterable

from fastapi import Depends, HTTPException, status

from wow_shop.api.dependencies.auth import CurrentUser, get_current_user
from wow_shop.modules.auth.infrastructure.db.models import UserRole


class RoleAccessValidator:
    def __init__(
        self,
        *,
        allowed_roles: Iterable[UserRole],
        detail: str,
    ) -> None:
        self._allowed_roles = frozenset(allowed_roles)
        self._detail = detail

    def __call__(
        self,
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        try:
            role = UserRole(current_user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=self._detail,
            ) from None

        if role not in self._allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=self._detail,
            )
        return current_user


def require_roles(
    *roles: UserRole,
    detail: str = "Not enough permissions.",
) -> RoleAccessValidator:
    if not roles:
        raise ValueError("At least one role is required.")
    return RoleAccessValidator(allowed_roles=roles, detail=detail)


require_admin_access = require_roles(
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.OPERATOR,
    UserRole.CONTENT_MANAGER,
    detail="Admin access required.",
)
require_booster_access = require_roles(
    UserRole.BOOSTER,
    detail="Booster access required.",
)
