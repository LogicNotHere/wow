from __future__ import annotations

from typing import Annotated

from fastapi import Header, Depends

from wow_shop.infrastructure.security.token_errors import (
    TokenInvalidError,
)
from wow_shop.infrastructure.security.token_service import (
    TokenService,
    get_token_service,
)
from wow_shop.infrastructure.security.token_payloads import AccessPayload


def get_bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    if authorization is None:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise TokenInvalidError("Authorization header must be Bearer token.")
    return token


def get_access_payload(
    token: Annotated[str | None, Depends(get_bearer_token)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> AccessPayload | None:
    if token is None:
        return None
    return token_service.parse_access_token(token)
