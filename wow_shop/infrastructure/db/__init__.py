"""Database foundation for the modular monolith."""

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.models import metadata
from wow_shop.infrastructure.db.session import (
    close_dbs,
    handle_session,
    get_async_session_factory,
    get_engine,
    s,
)

__all__ = [
    "Base",
    "close_dbs",
    "handle_session",
    "get_async_session_factory",
    "get_engine",
    "metadata",
    "s",
]
