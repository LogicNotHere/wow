from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import Depends, Header, HTTPException, status

from wow_shop.infrastructure.security.token_errors import (
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
)
from wow_shop.infrastructure.security.token_payloads import AccessPayload
from wow_shop.infrastructure.security.token_service import (
    TokenService,
    get_token_service,
)


def _raise_token_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, TokenMissingError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing.",
        ) from exc
    if isinstance(exc, TokenExpiredError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired.",
        ) from exc
    if isinstance(exc, TokenInvalidError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid.",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected token error.",
    ) from exc


def get_bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token.",
        )
    return token


def get_access_payload(
    token: Annotated[str, Depends(get_bearer_token)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> AccessPayload:
    try:
        return token_service.parse_access_token(token)
    except (TokenMissingError, TokenExpiredError, TokenInvalidError) as exc:
        _raise_token_http_error(exc)

