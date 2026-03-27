from __future__ import annotations

from contextvars import ContextVar

from pydantic import BaseModel, ConfigDict

from wow_shop.modules.auth.infrastructure.db.models import UserRole


class CurrentUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    role: UserRole
    jti: str
    exp: int


_current_user_ctx: ContextVar[CurrentUser | None] = ContextVar(
    "current_user_ctx",
    default=None,
)


class CurrentUserHolder:
    @property
    def user(self) -> CurrentUser | None:
        return _current_user_ctx.get()

    @user.setter
    def user(self, value: CurrentUser | None) -> None:
        _current_user_ctx.set(value)


cu = CurrentUserHolder()


def get_auth_user() -> CurrentUser | None:
    return cu.user


def set_auth_user(user: CurrentUser | None) -> None:
    cu.user = user


def get_auth_user_id() -> int | None:
    user = cu.user
    if user is None:
        return None
    return user.user_id


def get_auth_user_role() -> UserRole | None:
    user = cu.user
    if user is None:
        return None
    return user.role

