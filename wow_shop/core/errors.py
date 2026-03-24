from __future__ import annotations

from typing import Any

from starlette import status

from wow_shop.shared.contracts.models import BaseHttpResponseModel


class ApplicationError(Exception):
    """Base application error."""


class ApiException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Request failed."

    def __init__(
        self,
        message: str | None = None,
        data: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        self.message = message or self.default_message
        self.data = data
        super().__init__(self.message)

    def get_content(self) -> BaseHttpResponseModel[Any]:
        return BaseHttpResponseModel[Any](
            status="error",
            message=self.message,
            data=self.data,
        )


class BadRequestApiException(ApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Bad request."


class UnauthorizedApiException(ApiException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Unauthorized."


class ForbiddenApiException(ApiException):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "Forbidden."


class NotFoundApiException(ApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Not found."


class ConflictApiException(ApiException):
    status_code = status.HTTP_409_CONFLICT
    default_message = "Conflict."


class ServiceUnavailableApiException(ApiException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "Service unavailable."


class InternalApiException(ApiException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Cannot process request."
