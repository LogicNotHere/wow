from contextvars import Token, ContextVar
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
db_session_ctx: ContextVar[AsyncSession | None] = ContextVar(
    "db_session_ctx",
    default=None,
)


class Sessions:
    @property
    def db(self) -> AsyncSession:
        session = db_session_ctx.get()
        if session is None:
            raise RuntimeError("Database session is not initialized.")
        return session

    @db.setter
    def db(self, value: AsyncSession) -> None:
        db_session_ctx.set(value)


s = Sessions()


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


async def close_dbs() -> None:
    global engine
    global AsyncSessionFactory

    if engine is None:
        return

    await engine.dispose()
    engine = None
    AsyncSessionFactory = None


async def handle_session() -> AsyncGenerator[None, None]:
    _init_db_infra()
    assert AsyncSessionFactory is not None

    async with AsyncSessionFactory() as session:
        token: Token[AsyncSession | None] = db_session_ctx.set(session)
        try:
            yield
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            db_session_ctx.reset(token)
