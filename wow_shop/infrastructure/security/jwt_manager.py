from __future__ import annotations

from uuid import uuid4
from typing import Any
from datetime import datetime, timezone, timedelta
from functools import lru_cache

import jwt

from wow_shop.core.config_loader import get_settings
from wow_shop.infrastructure.security.token_errors import (
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
)
from wow_shop.infrastructure.security.token_payloads import TokenType


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


class JwtManager:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        issuer: str,
        access_ttl_minutes: int,
        refresh_ttl_days: int,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._issuer = issuer
        self._access_ttl_minutes = access_ttl_minutes
        self._refresh_ttl_days = refresh_ttl_days

    def build_access_token(self, user_id: int, role: str) -> str:
        payload = self._build_base_payload(
            user_id=user_id,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=self._access_ttl_minutes),
        )
        payload["role"] = role
        return self._encode(payload)

    def build_refresh_token(self, user_id: int) -> str:
        payload = self._build_base_payload(
            user_id=user_id,
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(days=self._refresh_ttl_days),
        )
        return self._encode(payload)

    def decode_token(self, token: str) -> dict[str, Any]:
        if not token:
            raise TokenMissingError("Token is required.")

        try:
            payload = jwt.decode(
                token,
                key=self._secret_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError("Token expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise TokenInvalidError("Token invalid.") from exc

        if not isinstance(payload, dict):
            raise TokenInvalidError("Token payload must be a JSON object.")
        return payload

    def _build_base_payload(
        self,
        *,
        user_id: int,
        token_type: TokenType,
        expires_delta: timedelta,
    ) -> dict[str, Any]:
        if user_id <= 0:
            raise TokenInvalidError("User id must be positive.")

        issued_at = _now_utc()
        expires_at = issued_at + expires_delta
        return {
            "sub": str(user_id),
            "jti": str(uuid4()),
            "iss": self._issuer,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "type": token_type.value,
        }

    def _encode(self, payload: dict[str, Any]) -> str:
        token = jwt.encode(
            payload,
            key=self._secret_key,
            algorithm=self._algorithm,
        )
        if not isinstance(token, str):
            raise TokenInvalidError("JWT encode failed.")
        return token


@lru_cache
def get_jwt_manager() -> JwtManager:
    settings = get_settings()
    return JwtManager(
        secret_key=settings.jwt.secret_key,
        algorithm=settings.jwt.algorithm,
        issuer=settings.jwt.issuer,
        access_ttl_minutes=settings.jwt.access_ttl_minutes,
        refresh_ttl_days=settings.jwt.refresh_ttl_days,
    )
