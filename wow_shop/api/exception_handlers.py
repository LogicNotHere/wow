from __future__ import annotations

import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from wow_shop.core.errors import (
    ApiException,
    ApplicationError,
    ConflictApiException,
    InternalApiException,
    BadRequestApiException,
    NotFoundApiException,
    UnauthorizedApiException,
)
from wow_shop.modules.auth.application.errors import (
    AuthValidationError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
)
from wow_shop.modules.catalog.application.errors import (
    CatalogValidationError,
    ParentCategoryNotFoundError,
    CategoryAlreadyExistsError,
    GameAlreadyExistsError,
    GameNotFoundError,
)
from wow_shop.infrastructure.security.token_errors import (
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
    RefreshTokenRevokedError,
    RefreshTokenConflictError,
)

log = logging.getLogger(__name__)


def _map_application_error(exc: ApplicationError) -> ApiException:
    if isinstance(exc, (AuthValidationError, CatalogValidationError)):
        return BadRequestApiException(str(exc))

    if isinstance(
        exc,
        (
            TokenMissingError,
            TokenInvalidError,
            TokenExpiredError,
            RefreshTokenRevokedError,
            InvalidCredentialsError,
        ),
    ):
        return UnauthorizedApiException(str(exc))

    if isinstance(exc, (ParentCategoryNotFoundError, GameNotFoundError)):
        return NotFoundApiException(str(exc))

    if isinstance(exc, (UserAlreadyExistsError, RefreshTokenConflictError)):
        return ConflictApiException(str(exc))

    if isinstance(exc, (CategoryAlreadyExistsError, GameAlreadyExistsError)):
        return ConflictApiException(str(exc))

    return InternalApiException()


async def api_exception_handler(
    request: Request, exc: ApiException
) -> JSONResponse:
    log.error("While processing route %s: ", request.url, exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.get_content().model_dump(mode="json"),
    )


async def application_exception_handler(
    request: Request, exc: ApplicationError
) -> JSONResponse:
    mapped = _map_application_error(exc)
    return await api_exception_handler(request, mapped)


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    mapped = ApiException(
        message=message,
        status_code=exc.status_code,
    )
    return await api_exception_handler(request, mapped)


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return await api_exception_handler(request, InternalApiException())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiException, api_exception_handler)
    app.add_exception_handler(ApplicationError, application_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
