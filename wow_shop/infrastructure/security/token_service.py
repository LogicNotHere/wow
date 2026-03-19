from __future__ import annotations

from time import time
from functools import lru_cache

from wow_shop.infrastructure.security.jwt_manager import (
    JwtManager,
    get_jwt_manager,
)
from wow_shop.infrastructure.security.token_errors import (
    RefreshTokenRevokedError,
)
from wow_shop.infrastructure.security.token_payloads import (
    TokenPair,
    AccessPayload,
    RefreshPayload,
)
from wow_shop.infrastructure.security.refresh_token_store import (
    RefreshTokenStore,
)
from wow_shop.infrastructure.security.redis_refresh_token_store import (
    get_refresh_token_store,
)


class TokenService:
    def __init__(
        self,
        *,
        jwt_manager: JwtManager,
        refresh_store: RefreshTokenStore,
    ) -> None:
        self._jwt_manager = jwt_manager
        self._refresh_store = refresh_store

    async def issue_token_pair(self, user_id: int, role: str) -> TokenPair:
        access_token = self._jwt_manager.build_access_token(
            user_id=user_id,
            role=role,
        )
        refresh_token = self._jwt_manager.build_refresh_token(user_id=user_id)
        refresh_payload = self._parse_refresh_payload(refresh_token)
        await self._save_refresh_payload(refresh_payload)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, refresh_token: str, role: str) -> TokenPair:
        old_payload = self._parse_refresh_payload(refresh_token)
        await self._ensure_refresh_token_active(old_payload.jti)

        new_refresh_token = self._jwt_manager.build_refresh_token(
            user_id=old_payload.user_id
        )
        new_refresh_payload = self._parse_refresh_payload(new_refresh_token)
        await self._save_refresh_payload(new_refresh_payload)
        await self._refresh_store.delete(old_payload.jti)

        new_access_token = self._jwt_manager.build_access_token(
            user_id=old_payload.user_id,
            role=role,
        )
        return TokenPair(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    def parse_access_token(self, token: str) -> AccessPayload:
        payload = self._jwt_manager.decode_token(token)
        return AccessPayload.from_payload(payload)

    def parse_refresh_token(self, token: str) -> RefreshPayload:
        payload = self._jwt_manager.decode_token(token)
        return RefreshPayload.from_payload(payload)

    async def logout_refresh_token(self, refresh_token: str) -> None:
        payload = self.parse_refresh_token(refresh_token)
        await self._refresh_store.delete(payload.jti)

    def _parse_refresh_payload(self, token: str) -> RefreshPayload:
        return self.parse_refresh_token(token)

    async def _save_refresh_payload(self, payload: RefreshPayload) -> None:
        ttl = self._seconds_to_expire(payload.exp)
        await self._refresh_store.save(
            jti=payload.jti,
            user_id=payload.user_id,
            ttl=ttl,
        )

    async def _ensure_refresh_token_active(self, jti: str) -> None:
        if not await self._refresh_store.exists(jti):
            raise RefreshTokenRevokedError("Refresh token revoked.")

    def _seconds_to_expire(self, exp: int) -> int:
        return max(exp - int(time()), 1)


@lru_cache
def get_token_service() -> TokenService:
    return TokenService(
        jwt_manager=get_jwt_manager(),
        refresh_store=get_refresh_token_store(),
    )
