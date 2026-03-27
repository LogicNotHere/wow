from __future__ import annotations

from wow_shop.modules.auth.api.request.types import (
    NonEmptyStr,
    NonEmptyStrippedStr,
    PasswordStr,
)
from wow_shop.shared.contracts import BaseRequestModel


class RegisterRequest(BaseRequestModel):
    email: NonEmptyStrippedStr
    password: PasswordStr


class LoginRequest(BaseRequestModel):
    email: NonEmptyStrippedStr
    password: NonEmptyStr


class RefreshRequest(BaseRequestModel):
    refresh_token: NonEmptyStrippedStr


class LogoutRequest(BaseRequestModel):
    refresh_token: NonEmptyStrippedStr
