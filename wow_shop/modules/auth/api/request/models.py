from __future__ import annotations

from pydantic import Field

from wow_shop.shared.contracts import BaseRequestModel


class RegisterRequest(BaseRequestModel):
    email: str
    password: str = Field(min_length=8)


class LoginRequest(BaseRequestModel):
    email: str
    password: str


class RefreshRequest(BaseRequestModel):
    refresh_token: str


class LogoutRequest(BaseRequestModel):
    refresh_token: str
