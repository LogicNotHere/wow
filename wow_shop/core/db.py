from wow_shop.core.config_loader import get_settings
from wow_shop.infrastructure.db.session import (
    s,
    close_dbs,
    get_engine,
    handle_session,
    get_async_session_factory,
)


def get_database_url() -> str:
    settings = get_settings()
    return settings.db.url
