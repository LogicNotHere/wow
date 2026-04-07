from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from collections.abc import Sequence

from sqlalchemy import or_
from sqlalchemy.sql import Select


class ApplicableFilter(Protocol):
    def apply(self, query: Select[Any]) -> Select[Any]:
        ...


@dataclass(slots=True)
class ExactFilter:
    field: Any
    value: Any | None

    def apply(self, query: Select[Any]) -> Select[Any]:
        if self.value is None:
            return query
        return query.where(self.field == self.value)


@dataclass(slots=True)
class SearchILikeFilter:
    fields: Sequence[Any]
    value: str | None

    def apply(self, query: Select[Any]) -> Select[Any]:
        if self.value is None:
            return query

        normalized_search = self.value.strip()
        if not normalized_search:
            return query

        search_pattern = f"%{normalized_search}%"
        return query.where(
            or_(*(field.ilike(search_pattern) for field in self.fields))
        )


@dataclass(slots=True)
class ClauseFilter:
    clause: Any | None

    def apply(self, query: Select[Any]) -> Select[Any]:
        if self.clause is None:
            return query
        return query.where(self.clause)


def apply_filters(
    query: Select[Any],
    filters: Sequence[ApplicableFilter],
) -> Select[Any]:
    for query_filter in filters:
        query = query_filter.apply(query)
    return query
