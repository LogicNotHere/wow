from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status

from wow_shop.modules.auth.infrastructure.db.models import UserRole
from wow_shop.shared.auth.context import CurrentUser, get_auth_user


class RoleAccessValidator:
    def __init__(
        self,
        *,
        allowed_roles: Iterable[UserRole],
        detail: str,
        unauthenticated_detail: str = "Authorization required.",
        invalid_role_detail: str = "Invalid auth role context.",
    ) -> None:
        self._allowed_roles = frozenset(allowed_roles)
        self._detail = detail
        self._unauthenticated_detail = unauthenticated_detail
        self._invalid_role_detail = invalid_role_detail

    async def __call__(self) -> CurrentUser:
        current_user = get_auth_user()
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self._unauthenticated_detail,
            )

        if not isinstance(current_user.role, UserRole):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=self._invalid_role_detail,
            )

        if current_user.role not in self._allowed_roles:
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


CATALOG_STAFF_ROLES = (
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.OPERATOR,
    UserRole.CONTENT_MANAGER,
)

require_catalog_deleted_view_access = require_roles(
    *CATALOG_STAFF_ROLES,
    detail="Not enough permissions.",
)
require_catalog_soft_delete_access = require_roles(
    *CATALOG_STAFF_ROLES,
    detail="Not enough permissions.",
)
require_catalog_restore_access = require_roles(
    *CATALOG_STAFF_ROLES,
    detail="Not enough permissions.",
)


def ensure_catalog_deleted_view_access(role: UserRole | None) -> None:
    if role not in CATALOG_STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions.",
        )
