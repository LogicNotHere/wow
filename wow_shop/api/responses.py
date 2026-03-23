from __future__ import annotations

from typing import Any

from starlette import status

from wow_shop.shared.contracts import BaseHttpResponseModel

ErrorResponseModel = BaseHttpResponseModel[dict[str, Any]]

COMMON_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponseModel,
        "description": "Provided wrong data.",
    },
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponseModel,
        "description": "Authorization failed.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponseModel,
        "description": "Not enough permissions.",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponseModel,
        "description": "Resource not found.",
    },
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponseModel,
        "description": "Resource conflict.",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponseModel,
        "description": "Service unavailable.",
    },
}
