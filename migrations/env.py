from __future__ import annotations

from logging.config import fileConfig
import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from wow_shop.infrastructure.db.models import metadata as target_metadata


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _load_dotenv_if_present() -> None:
    """Minimal .env loader for host-based runs without external deps."""
    env_file = Path(".env")
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _as_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
            1,
        )
    return database_url


def _get_database_url() -> str:
    _load_dotenv_if_present()
    raw_url = os.getenv("DATABASE_URL")
    if raw_url:
        return _as_sync_database_url(raw_url)

    try:
        from wow_shop.core.config_loader import load_settings

        settings = load_settings()
        return _as_sync_database_url(settings.db.url)
    except Exception as exc:
        raise RuntimeError(
            "Failed to load database URL from DATABASE_URL or YAML config."
        ) from exc


def run_migrations_offline() -> None:
    database_url = _get_database_url()
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database_url = _get_database_url()
    config.set_main_option("sqlalchemy.url", database_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
