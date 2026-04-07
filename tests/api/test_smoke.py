from __future__ import annotations

from typing import Callable

from httpx import AsyncClient
from wow_shop.modules.auth.infrastructure.db.models import UserRole


async def test_api_smoke_health_public_and_staff(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
) -> None:
    health_response = await client.get("/health")

    assert health_response.status_code == 200
    health_body = health_response.json()
    assert health_body["status"] == "ok"
    assert isinstance(health_body["environment"], str)

    response = await client.get("/api/v1/games/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"] is not None
    assert isinstance(body["data"].get("items"), list)

    staff_response = await client.get(
        "/api/v1/admin/promotions/",
        headers=auth_headers(role=UserRole.ADMIN),
    )
    assert staff_response.status_code == 200
