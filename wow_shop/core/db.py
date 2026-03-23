from wow_shop.core.config_loader import get_settings
from wow_shop.infrastructure.db.session import (
    get_engine,
    get_db_session,
    get_async_session_factory,
)


def get_database_url() -> str:
    settings = get_settings()
    return settings.db.url


__all__ = [
    "get_async_session_factory",
    "get_engine",
    "get_database_url",
    "get_db_session",
]
