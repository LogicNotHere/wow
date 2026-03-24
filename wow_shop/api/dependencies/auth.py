from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel, ConfigDict

from wow_shop.api.dependencies.token import get_access_payload
from wow_shop.infrastructure.security.token_payloads import AccessPayload


class CurrentUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    role: str
    jti: str
    exp: int


def get_current_user(
    payload: Annotated[AccessPayload, Depends(get_access_payload)],
) -> CurrentUser:
    return CurrentUser(
        user_id=payload.user_id,
        role=payload.role,
        jti=payload.jti,
        exp=payload.exp,
    )
