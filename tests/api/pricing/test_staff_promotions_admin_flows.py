from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from wow_shop.modules.auth.infrastructure.db.models import (
    User,
    UserRole,
    UserStatus,
)
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServiceLotStatus,
)
from wow_shop.shared.utils.time import now_utc


@dataclass(slots=True)
class PromotionsAdminSeed:
    staff_user: User
    target_user_a: User
    target_user_b: User
    game: Game
    category_main: ServiceCategory
    category_alt: ServiceCategory
    lot_main: ServiceLot
    lot_alt: ServiceLot


def _response_data(response: dict[str, Any]) -> dict[str, Any]:
    assert response["status"] == "success"
    data = response["data"]
    assert isinstance(data, dict)
    return data


def _response_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = _response_data(response)
    items = data.get("items")
    assert isinstance(items, list)
    return items


def _error_message(response: dict[str, Any]) -> str:
    assert response["status"] == "error"
    message = response["message"]
    assert isinstance(message, str)
    return message


async def _create_promotion(
    *,
    client: AsyncClient,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> int:
    response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    return _response_data(response.json())["id"]


@pytest_asyncio.fixture
async def promotions_admin_seed(
    db_session: AsyncSession,
) -> PromotionsAdminSeed:
    staff_user = User(
        email="admin@example.com",
        password_hash=None,
        status=UserStatus.ACTIVE,
        role=UserRole.ADMIN,
    )
    target_user_a = User(
        email="target-a@example.com",
        password_hash=None,
        status=UserStatus.ACTIVE,
        role=UserRole.CUSTOMER,
    )
    target_user_b = User(
        email="target-b@example.com",
        password_hash=None,
        status=UserStatus.ACTIVE,
        role=UserRole.CUSTOMER,
    )
    db_session.add_all([staff_user, target_user_a, target_user_b])
    await db_session.flush()

    game = Game(
        name="World of Warcraft",
        slug="wow",
        status=GameStatus.ACTIVE,
        sort_order=1,
    )
    db_session.add(game)
    await db_session.flush()

    category_main = ServiceCategory(
        game_id=game.id,
        name="Mythic Plus",
        slug="mythic-plus",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    category_alt = ServiceCategory(
        game_id=game.id,
        name="Raids",
        slug="raids",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=2,
    )
    db_session.add_all([category_main, category_alt])
    await db_session.flush()

    lot_main = ServiceLot(
        category_id=category_main.id,
        name="Main Lot",
        slug="main-lot",
        description="Main",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("20.00"),
    )
    lot_alt = ServiceLot(
        category_id=category_alt.id,
        name="Alt Lot",
        slug="alt-lot",
        description="Alt",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("30.00"),
    )
    db_session.add_all([lot_main, lot_alt])
    await db_session.commit()

    return PromotionsAdminSeed(
        staff_user=staff_user,
        target_user_a=target_user_a,
        target_user_b=target_user_b,
        game=game,
        category_main=category_main,
        category_alt=category_alt,
        lot_main=lot_main,
        lot_alt=lot_alt,
    )


@pytest.mark.regression_catalog_promotions
async def test_create_promotion_matrix(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    promotions_admin_seed: PromotionsAdminSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=promotions_admin_seed.staff_user.id,
    )
    now = now_utc()
    assignment_expires_at = (now + timedelta(days=30)).isoformat()

    public_lot_discount_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "public",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 20,
            "display_priority": 10,
        },
    )
    public_lot_discount_detail = await client.get(
        f"/api/v1/admin/promotions/{public_lot_discount_id}",
        headers=headers,
    )
    assert public_lot_discount_detail.status_code == 200
    detail_data = _response_data(public_lot_discount_detail.json())
    assert detail_data["audience"] == "public"
    assert detail_data["lot_id"] == promotions_admin_seed.lot_main.id
    assert detail_data["category_id"] is None
    assert detail_data["discount_type"] == "percent"
    assert detail_data["discount_percent_value"] == 20

    public_lot_badge_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "public",
            "lot_id": promotions_admin_seed.lot_alt.id,
            "badge_tag": "hot",
            "display_priority": 3,
        },
    )
    public_lot_badge_detail = await client.get(
        f"/api/v1/admin/promotions/{public_lot_badge_id}",
        headers=headers,
    )
    assert public_lot_badge_detail.status_code == 200
    detail_data = _response_data(public_lot_badge_detail.json())
    assert detail_data["badge_tag"] == "hot"
    assert detail_data["discount_type"] is None

    public_category_badge_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "public",
            "category_id": promotions_admin_seed.category_main.id,
            "badge_tag": "sale",
            "display_priority": 5,
        },
    )
    public_category_badge_detail = await client.get(
        f"/api/v1/admin/promotions/{public_category_badge_id}",
        headers=headers,
    )
    assert public_category_badge_detail.status_code == 200
    detail_data = _response_data(public_category_badge_detail.json())
    assert detail_data["audience"] == "public"
    assert detail_data["category_id"] == promotions_admin_seed.category_main.id
    assert detail_data["discount_type"] is None

    reject_public_category_discount_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "public",
            "category_id": promotions_admin_seed.category_alt.id,
            "discount_type": "percent",
            "discount_percent_value": 10,
        },
    )
    assert reject_public_category_discount_response.status_code == 400
    assert (
        _error_message(reject_public_category_discount_response.json())
        == "Public category promotion cannot contain pricing discount."
    )

    personal_lot_discount_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "personal",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "fixed_amount",
            "discount_amount_eur": "5.00",
            "target_user_id": promotions_admin_seed.target_user_a.id,
            "assignment_expires_at": assignment_expires_at,
        },
    )
    personal_lot_assignments_response = await client.get(
        f"/api/v1/admin/promotions/{personal_lot_discount_id}/assignments",
        headers=headers,
    )
    assert personal_lot_assignments_response.status_code == 200
    assignment_items = _response_items(personal_lot_assignments_response.json())
    assert len(assignment_items) == 1
    assert assignment_items[0]["user_id"] == promotions_admin_seed.target_user_a.id
    assert assignment_items[0]["is_one_time"] is True

    personal_category_discount_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "personal",
            "category_id": promotions_admin_seed.category_main.id,
            "discount_type": "percent",
            "discount_percent_value": 15,
            "target_user_id": promotions_admin_seed.target_user_b.id,
            "assignment_expires_at": assignment_expires_at,
        },
    )
    personal_category_detail = await client.get(
        f"/api/v1/admin/promotions/{personal_category_discount_id}",
        headers=headers,
    )
    assert personal_category_detail.status_code == 200
    detail_data = _response_data(personal_category_detail.json())
    assert detail_data["audience"] == "personal"
    assert detail_data["category_id"] == promotions_admin_seed.category_main.id
    assert detail_data["discount_type"] == "percent"
    assert detail_data["discount_percent_value"] == 15


@pytest.mark.regression_catalog_promotions
async def test_public_promotion_uniqueness_on_scope(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    promotions_admin_seed: PromotionsAdminSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=promotions_admin_seed.staff_user.id,
    )

    first_public_lot_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "public",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 5,
        },
    )
    assert first_public_lot_response.status_code == 201

    second_public_lot_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "public",
            "lot_id": promotions_admin_seed.lot_main.id,
            "badge_tag": "hot",
        },
    )
    assert second_public_lot_response.status_code == 400
    assert _error_message(second_public_lot_response.json()) == (
        "Public promotion for this lot already exists."
    )

    first_public_category_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "public",
            "category_id": promotions_admin_seed.category_main.id,
            "badge_tag": "sale",
        },
    )
    assert first_public_category_response.status_code == 201

    second_public_category_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "public",
            "category_id": promotions_admin_seed.category_main.id,
            "badge_tag": "new",
        },
    )
    assert second_public_category_response.status_code == 400
    assert _error_message(second_public_category_response.json()) == (
        "Public promotion for this category already exists."
    )


async def test_multiple_personal_promotions_on_same_scope_are_allowed(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    promotions_admin_seed: PromotionsAdminSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=promotions_admin_seed.staff_user.id,
    )
    assignment_expires_at = (now_utc() + timedelta(days=7)).isoformat()

    first_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "personal",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 10,
            "target_user_id": promotions_admin_seed.target_user_a.id,
            "assignment_expires_at": assignment_expires_at,
        },
    )
    assert first_response.status_code == 201
    first_id = _response_data(first_response.json())["id"]

    second_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "personal",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "fixed_amount",
            "discount_amount_eur": "3.00",
            "target_user_id": promotions_admin_seed.target_user_b.id,
            "assignment_expires_at": assignment_expires_at,
        },
    )
    assert second_response.status_code == 201
    second_id = _response_data(second_response.json())["id"]
    assert first_id != second_id

    list_response = await client.get(
        "/api/v1/admin/promotions/",
        headers=headers,
        params={
            "audience": "personal",
            "lot_slug": promotions_admin_seed.lot_main.slug,
            "limit": 50,
            "offset": 0,
        },
    )
    assert list_response.status_code == 200
    items = _response_items(list_response.json())
    returned_ids = {item["id"] for item in items}
    assert {first_id, second_id}.issubset(returned_ids)


async def test_patch_promotion_flow(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    promotions_admin_seed: PromotionsAdminSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=promotions_admin_seed.staff_user.id,
    )

    create_response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "public",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 10,
            "display_priority": 1,
        },
    )
    assert create_response.status_code == 201
    promotion_id = _response_data(create_response.json())["id"]

    patch_response = await client.patch(
        f"/api/v1/admin/promotions/{promotion_id}",
        headers=headers,
        json={
            "discount_percent_value": 25,
            "is_enabled": False,
            "badge_tag": "hit",
            "display_priority": 9,
        },
    )
    assert patch_response.status_code == 200
    patched_data = _response_data(patch_response.json())
    assert patched_data["discount_percent_value"] == 25
    assert patched_data["is_enabled"] is False
    assert patched_data["badge_tag"] == "hit"
    assert patched_data["display_priority"] == 9

    invalid_patch_response = await client.patch(
        f"/api/v1/admin/promotions/{promotion_id}",
        headers=headers,
        json={"discount_amount_eur": "4.00"},
    )
    assert invalid_patch_response.status_code == 400
    assert _error_message(invalid_patch_response.json()) == (
        "discount_amount_eur can be changed only for FIXED_AMOUNT promotions."
    )


async def test_promotion_state_filters(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    promotions_admin_seed: PromotionsAdminSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=promotions_admin_seed.staff_user.id,
    )
    now = now_utc()
    expires_at = (now + timedelta(days=30)).isoformat()

    active_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "personal",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 5,
            "is_enabled": True,
            "starts_at": (now - timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=1)).isoformat(),
            "target_user_id": promotions_admin_seed.target_user_a.id,
            "assignment_expires_at": expires_at,
        },
    )
    scheduled_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "personal",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 7,
            "is_enabled": True,
            "starts_at": (now + timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=2)).isoformat(),
            "target_user_id": promotions_admin_seed.target_user_a.id,
            "assignment_expires_at": expires_at,
        },
    )
    expired_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "personal",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 9,
            "is_enabled": True,
            "starts_at": (now - timedelta(days=3)).isoformat(),
            "ends_at": (now - timedelta(hours=1)).isoformat(),
            "target_user_id": promotions_admin_seed.target_user_a.id,
            "assignment_expires_at": expires_at,
        },
    )
    disabled_id = await _create_promotion(
        client=client,
        headers=headers,
        payload={
            "audience": "personal",
            "lot_id": promotions_admin_seed.lot_main.id,
            "discount_type": "percent",
            "discount_percent_value": 11,
            "is_enabled": False,
            "starts_at": (now - timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=1)).isoformat(),
            "target_user_id": promotions_admin_seed.target_user_a.id,
            "assignment_expires_at": expires_at,
        },
    )

    active_list_response = await client.get(
        "/api/v1/admin/promotions/",
        headers=headers,
        params={"state": "active", "audience": "personal", "limit": 50},
    )
    assert active_list_response.status_code == 200
    active_ids = {item["id"] for item in _response_items(active_list_response.json())}
    assert active_ids == {active_id}

    scheduled_list_response = await client.get(
        "/api/v1/admin/promotions/",
        headers=headers,
        params={"state": "scheduled", "audience": "personal", "limit": 50},
    )
    assert scheduled_list_response.status_code == 200
    scheduled_ids = {
        item["id"] for item in _response_items(scheduled_list_response.json())
    }
    assert scheduled_ids == {scheduled_id}

    expired_list_response = await client.get(
        "/api/v1/admin/promotions/",
        headers=headers,
        params={"state": "expired", "audience": "personal", "limit": 50},
    )
    assert expired_list_response.status_code == 200
    expired_ids = {item["id"] for item in _response_items(expired_list_response.json())}
    assert expired_ids == {expired_id}

    disabled_list_response = await client.get(
        "/api/v1/admin/promotions/",
        headers=headers,
        params={"state": "disabled", "audience": "personal", "limit": 50},
    )
    assert disabled_list_response.status_code == 200
    disabled_ids = {
        item["id"] for item in _response_items(disabled_list_response.json())
    }
    assert disabled_ids == {disabled_id}
