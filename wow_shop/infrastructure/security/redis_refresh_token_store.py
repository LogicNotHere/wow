from __future__ import annotations

import json
from functools import lru_cache

from redis.asyncio import Redis, from_url as redis_from_url

from wow_shop.core.config_loader import get_settings
from wow_shop.infrastructure.security.token_errors import (
    RefreshTokenConflictError,
)
from wow_shop.infrastructure.security.refresh_token_store import (
    RefreshTokenStore,
)


def _refresh_key(jti: str) -> str:
    return f"refresh:{jti}"


class RedisRefreshTokenStore(RefreshTokenStore):
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def save(self, jti: str, user_id: int, ttl: int) -> None:
        key = _refresh_key(jti)
        payload = json.dumps({"user_id": user_id}, separators=(",", ":"))
        created = await self._redis.set(
            name=key,
            value=payload,
            ex=ttl,
            nx=True,
        )
        if not created:
            raise RefreshTokenConflictError("Refresh token jti already exists.")

    async def exists(self, jti: str) -> bool:
        key = _refresh_key(jti)
        return bool(await self._redis.exists(key))

    async def delete(self, jti: str) -> None:
        key = _refresh_key(jti)
        await self._redis.delete(key)


@lru_cache
def get_redis_client() -> Redis:
    settings = get_settings()
    return redis_from_url(
        settings.redis.url,
        encoding="utf-8",
        decode_responses=True,
    )


@lru_cache
def get_refresh_token_store() -> RefreshTokenStore:
    return RedisRefreshTokenStore(get_redis_client())


async def close_redis_client() -> None:
    if get_redis_client.cache_info().currsize > 0:
        redis_client = get_redis_client()
        await redis_client.aclose()

    get_refresh_token_store.cache_clear()
    get_redis_client.cache_clear()
