from wow_shop.core.config import settings
from wow_shop.infrastructure.db.session import AsyncSessionFactory, engine, get_db_session


def get_database_url() -> str:
    return settings.database_url


__all__ = [
    "AsyncSessionFactory",
    "engine",
    "get_database_url",
    "get_db_session",
]
