from __future__ import annotations

import asyncio
import os
from typing import Any
from collections.abc import AsyncIterator, Callable, Iterator

import psycopg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from wow_shop.core.config_loader import get_settings, init_config
from wow_shop.infrastructure.db.models import metadata
from wow_shop.infrastructure.db.session import (
    get_async_session_factory,
    get_engine,
)
from wow_shop.infrastructure.db.session import close_dbs
from wow_shop.modules.auth.infrastructure.db.models import UserRole
from tests.helpers.auth import public_headers, staff_headers

os.environ["CONFIG"] = "config/base.yaml"
os.environ["OVERRIDE_CONFIG"] = "config/test.yaml"
init_config(
    config_path="config/base.yaml",
    override_config_path="config/test.yaml",
)
settings = get_settings()
test_db_url = os.getenv("WOWSHOP_TEST_DB_URL")
if test_db_url:
    settings.db.url = test_db_url

from wow_shop.app import app as wowshop_app


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


def _ensure_test_database_exists() -> None:
    db_url = make_url(get_settings().db.url)
    test_db_name = db_url.database
    if test_db_name is None:
        raise RuntimeError("Test DB name is missing in settings.db.url")

    admin_db_name = os.getenv("WOWSHOP_TEST_ADMIN_DB", "postgres")
    with psycopg.connect(
        host=db_url.host,
        port=db_url.port,
        user=db_url.username,
        password=db_url.password,
        dbname=admin_db_name,
        autocommit=True,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()"
                ),
                (test_db_name,),
            )
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(test_db_name)
                )
            )
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(test_db_name)
                )
            )


async def _bootstrap_test_schema() -> None:
    bootstrap_engine = create_async_engine(
        get_settings().db.url,
        future=True,
        pool_pre_ping=True,
    )
    try:
        async with bootstrap_engine.begin() as connection:
            await connection.run_sync(metadata.create_all)
    finally:
        await bootstrap_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> None:
    _ensure_test_database_exists()
    asyncio.run(_bootstrap_test_schema())


@pytest_asyncio.fixture
async def clean_database() -> AsyncIterator[None]:
    engine = get_engine()
    # TRUNCATE ... CASCADE does not require FK-aware ordering.
    table_names = list(metadata.tables.keys())
    truncate_sql = (
        "TRUNCATE TABLE "
        + ", ".join(f'"{table_name}"' for table_name in table_names)
        + " RESTART IDENTITY CASCADE"
    )
    async with engine.begin() as connection:
        await connection.execute(text(truncate_sql))
    try:
        yield
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(truncate_sql))


@pytest_asyncio.fixture
async def db_session(clean_database: None) -> AsyncIterator[AsyncSession]:
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app() -> AsyncIterator[Any]:
    yield wowshop_app


@pytest_asyncio.fixture
async def client(app: Any, clean_database: None) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=True,
    ) as async_client:
        yield async_client


@pytest.fixture
def auth_headers() -> Callable[..., dict[str, str]]:
    def _build_headers(
        *,
        role: UserRole | None = None,
        user_id: int = 1,
    ) -> dict[str, str]:
        if role is None:
            return public_headers()
        return staff_headers(role=role, user_id=user_id)

    return _build_headers


@pytest_asyncio.fixture(scope="session", autouse=True)
async def teardown_test_infra() -> AsyncIterator[None]:
    try:
        yield
    finally:
        await close_dbs()
