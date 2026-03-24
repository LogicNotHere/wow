from __future__ import annotations

from enum import Enum
from typing import Any, Self, Generic, TypeVar
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")
ItemT = TypeVar("ItemT")
MetaT = TypeVar("MetaT")


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class ORJsonModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )


class BaseRequestModel(ORJsonModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class BaseResponseDataModel(ORJsonModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    @classmethod
    def build(cls, **data: Any) -> Self:
        return cls(**data)


class BaseHttpResponseModel(ORJsonModel, Generic[T]):
    data: T | None = None
    message: str | None = None
    status: str = ResponseStatus.SUCCESS.value


class ListResponseItems(BaseResponseDataModel, Generic[ItemT]):
    items: list[ItemT]

    @classmethod
    def from_items(cls, items: Sequence[ItemT]) -> "ListResponseItems[ItemT]":
        return cls.build(items=list(items))


class ListResponseData(BaseResponseDataModel, Generic[ItemT, MetaT]):
    items: list[ItemT]
    meta: MetaT

    @classmethod
    def with_meta(
        cls,
        *,
        items: Sequence[ItemT],
        meta: MetaT,
    ) -> "ListResponseData[ItemT, MetaT]":
        return cls.build(items=list(items), meta=meta)
