from __future__ import annotations

from enum import Enum
from typing import Any, Mapping
from dataclasses import dataclass

from wow_shop.infrastructure.security.token_errors import TokenInvalidError


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def _read_required_str(payload: Mapping[str, Any], field_name: str) -> str:
    raw_value = payload.get(field_name)
    if not isinstance(raw_value, str) or not raw_value:
        raise TokenInvalidError(f"Token payload has invalid '{field_name}'.")
    return raw_value


def _read_required_int(payload: Mapping[str, Any], field_name: str) -> int:
    raw_value = payload.get(field_name)
    if not isinstance(raw_value, int):
        raise TokenInvalidError(f"Token payload has invalid '{field_name}'.")
    return raw_value


def read_user_id(payload: Mapping[str, Any]) -> int:
    raw_sub = payload.get("sub")
    if isinstance(raw_sub, str) and raw_sub.isdigit():
        return int(raw_sub)
    raise TokenInvalidError("Token payload has invalid 'sub'.")


def read_token_type(payload: Mapping[str, Any]) -> TokenType:
    raw_type = _read_required_str(payload, "type")
    try:
        return TokenType(raw_type)
    except ValueError as exc:
        raise TokenInvalidError("Token payload has invalid 'type'.") from exc


@dataclass(frozen=True, slots=True)
class BasePayload:
    user_id: int
    jti: str
    iat: int
    exp: int
    token_type: TokenType


@dataclass(frozen=True, slots=True)
class AccessPayload(BasePayload):
    role: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AccessPayload":
        token_type = read_token_type(payload)
        if token_type is not TokenType.ACCESS:
            raise TokenInvalidError("Expected access token.")

        return cls(
            user_id=read_user_id(payload),
            role=_read_required_str(payload, "role"),
            jti=_read_required_str(payload, "jti"),
            iat=_read_required_int(payload, "iat"),
            exp=_read_required_int(payload, "exp"),
            token_type=token_type,
        )


@dataclass(frozen=True, slots=True)
class RefreshPayload(BasePayload):
    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RefreshPayload":
        token_type = read_token_type(payload)
        if token_type is not TokenType.REFRESH:
            raise TokenInvalidError("Expected refresh token.")

        return cls(
            user_id=read_user_id(payload),
            jti=_read_required_str(payload, "jti"),
            iat=_read_required_int(payload, "iat"),
            exp=_read_required_int(payload, "exp"),
            token_type=token_type,
        )


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
