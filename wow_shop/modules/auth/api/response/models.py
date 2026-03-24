from __future__ import annotations

from typing import Self

from wow_shop.shared.contracts import BaseResponseDataModel
from wow_shop.infrastructure.security.token_payloads import TokenPair


class TokenPairResponse(BaseResponseDataModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def build(cls, token_pair: TokenPair) -> Self:
        return cls(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
        )
