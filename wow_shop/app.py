from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI

from wow_shop.api.dependencies.app import handle_request_id, log_request
from wow_shop.api.router import (
    admin_router,
    auth_public_router,
    booster_router,
    customer_router,
)
from wow_shop.core.config_loader import Config, init_config
from wow_shop.infrastructure.security.redis_refresh_token_store import (
    close_redis_client,
    get_redis_client,
)

init_config()
assert Config.c is not None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    get_redis_client()
    try:
        yield
    finally:
        await close_redis_client()


app = FastAPI(
    title="WowShop API",
    debug=Config.c.app.debug,
    openapi_url="/openapi.json",
    lifespan=lifespan,
    dependencies=[
        Depends(handle_request_id),
        Depends(log_request),
        #Depends(populate_sentry_tags)
    ],
)
app.include_router(auth_public_router, prefix="/api/v1/auth")
app.include_router(customer_router, prefix="/api/v1/auth")
app.include_router(booster_router, prefix="/api/v1/booster")
app.include_router(admin_router, prefix="/api/v1/admin")


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": Config.c.app.env,
    }
