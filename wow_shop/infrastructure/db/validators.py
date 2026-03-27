from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

MODEL_T = TypeVar("MODEL_T")


async def get_existing_by_field(
    *,
    session: AsyncSession,
    model: type[MODEL_T],
    field: InstrumentedAttribute[Any],
    value: Any,
    exclude_id: int | None = None,
    id_field: InstrumentedAttribute[Any] | None = None,
) -> MODEL_T | None:
    query = select(model).where(field == value)

    if exclude_id is not None:
        resolved_id_field = id_field
        if resolved_id_field is None:
            resolved_id_field = getattr(model, "id", None)
        if resolved_id_field is None:
            raise ValueError(
                "id_field is required when model has no 'id' attribute."
            )
        query = query.where(resolved_id_field != exclude_id)

    result = await session.execute(query.limit(1))
    return result.scalar_one_or_none()

