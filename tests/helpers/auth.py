from __future__ import annotations

from wow_shop.modules.auth.infrastructure.db.models import UserRole
from wow_shop.infrastructure.security.jwt_manager import get_jwt_manager


def public_headers() -> dict[str, str]:
    return {}


def staff_headers(
    *,
    role: UserRole = UserRole.ADMIN,
    user_id: int = 1,
) -> dict[str, str]:
    token = get_jwt_manager().build_access_token(
        user_id=user_id,
        role=role.value,
    )
    return {"Authorization": f"Bearer {token}"}
