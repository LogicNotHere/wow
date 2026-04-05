from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Self, TypeVar
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


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


ItemDataType = TypeVar("ItemDataType", bound=BaseResponseDataModel)
MetaDataType = TypeVar("MetaDataType", bound=BaseResponseDataModel)


class ListResponses(
    BaseResponseDataModel,
    Generic[ItemDataType, MetaDataType],
):
    items: list[ItemDataType]
    meta: MetaDataType | None = None

    @classmethod
    def with_meta(
        cls,
        *,
        items: Sequence[ItemDataType],
        meta: MetaDataType | None = None,
    ) -> "ListResponses[ItemDataType, MetaDataType]":
        return cls(items=list(items), meta=meta)


class ListResponsesOnce(BaseResponseDataModel, Generic[ItemDataType]):
    items: list[ItemDataType]

    @classmethod
    def from_items(
        cls,
        *,
        items: Sequence[ItemDataType],
    ) -> "ListResponsesOnce[ItemDataType]":
        return cls(items=list(items))
