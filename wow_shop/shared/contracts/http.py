from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseHttpResponseModel(BaseModel, Generic[T]):
    data: T | None = None
    message: str | None = None
    status: str = "success"
