from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from pydantic import ValidationError

from wow_shop.api.dependencies.token import get_access_payload
from wow_shop.infrastructure.security.token_errors import TokenInvalidRoleError
from wow_shop.infrastructure.security.token_payloads import AccessPayload
from wow_shop.shared.auth.context import CurrentUser, set_auth_user


async def get_current_user(
    payload: Annotated[AccessPayload | None, Depends(get_access_payload)],
) -> CurrentUser | None:
    if payload is None:
        set_auth_user(None)
        return None

    try:
        current_user = CurrentUser(
            user_id=payload.user_id,
            role=payload.role,
            jti=payload.jti,
            exp=payload.exp,
        )
    except ValidationError as exc:
        raise TokenInvalidRoleError("Token role is invalid.") from exc

    set_auth_user(current_user)
    return current_user
