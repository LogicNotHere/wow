"""Database foundation for the modular monolith."""

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.mixins import (
    CreateUpdateMixin,
    CreatedAtMixin,
    CreatedByMixin,
    UpdatedAtMixin,
    UpdatedByMixin,
)
from wow_shop.infrastructure.db.models import metadata
from wow_shop.infrastructure.db.session import (
    close_dbs,
    handle_session,
    get_async_session_factory,
    get_engine,
    s,
)
from wow_shop.infrastructure.db.types import (
    int_pk,
    str20,
    str32,
    str50,
    str100,
    str255,
    str1024,
)
from wow_shop.infrastructure.db.validators import get_existing_by_field

__all__ = [
    "Base",
    "CreateUpdateMixin",
    "CreatedAtMixin",
    "CreatedByMixin",
    "close_dbs",
    "handle_session",
    "int_pk",
    "get_async_session_factory",
    "get_engine",
    "metadata",
    "s",
    "get_existing_by_field",
    "str20",
    "str32",
    "str50",
    "str100",
    "str255",
    "str1024",
    "UpdatedAtMixin",
    "UpdatedByMixin",
]
