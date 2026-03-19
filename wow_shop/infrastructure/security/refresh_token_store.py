from __future__ import annotations

from typing import Protocol


class RefreshTokenStore(Protocol):
    async def save(self, jti: str, user_id: int, ttl: int) -> None:
        """Persist refresh token jti with TTL in seconds."""

    async def exists(self, jti: str) -> bool:
        """Return True if refresh token jti is active."""

    async def delete(self, jti: str) -> None:
        """Invalidate refresh token jti."""


#    async def rotate(
#        self,
#        *,
#        old_jti: str,
#        new_jti: str,
#        user_id: int,
#        ttl: int,
#    ) -> None:
#        """Rotate refresh token key from old jti to new jti.
#
#        Store must persist new key and invalidate old key as one logical step.
#        """
