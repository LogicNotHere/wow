from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from wow_shop.core.config_loader import get_settings

engine: AsyncEngine | None = None
AsyncSessionFactory: async_sessionmaker[AsyncSession] | None = None


def _init_db_infra() -> None:
    global engine
    global AsyncSessionFactory

    if engine is not None and AsyncSessionFactory is not None:
        return

    settings = get_settings()
    engine = create_async_engine(
        settings.db.url,
        echo=settings.app.debug,
        future=True,
        pool_pre_ping=True,
    )
    AsyncSessionFactory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )


def get_engine() -> AsyncEngine:
    _init_db_infra()
    assert engine is not None
    return engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    _init_db_infra()
    assert AsyncSessionFactory is not None
    return AsyncSessionFactory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    _init_db_infra()
    assert AsyncSessionFactory is not None

    async with AsyncSessionFactory() as session:
        yield session
