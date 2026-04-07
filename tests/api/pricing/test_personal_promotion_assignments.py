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
from wow_shop.modules.orders.infrastructure.db.models import (
    ExecutionMode,
    Order,
    OrderStatus,
)
from wow_shop.modules.pricing.infrastructure.db.models import PromotionUsage
from wow_shop.shared.utils.time import now_utc


@dataclass(slots=True)
class PersonalAssignmentsSeed:
    staff_user: User
    target_user_a: User
    target_user_b: User
    lot: ServiceLot


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


async def _create_personal_promotion(
    *,
    client: AsyncClient,
    headers: dict[str, str],
    lot_id: int,
    user_id: int,
    assignment_expires_at: str,
) -> int:
    response = await client.post(
        "/api/v1/admin/promotions/",
        headers=headers,
        json={
            "audience": "personal",
            "lot_id": lot_id,
            "discount_type": "percent",
            "discount_percent_value": 15,
            "target_user_id": user_id,
            "assignment_expires_at": assignment_expires_at,
        },
    )
    assert response.status_code == 201
    return _response_data(response.json())["id"]


@pytest_asyncio.fixture
async def personal_assignments_seed(
    db_session: AsyncSession,
) -> PersonalAssignmentsSeed:
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

    category = ServiceCategory(
        game_id=game.id,
        name="Mythic Plus",
        slug="mythic-plus",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    db_session.add(category)
    await db_session.flush()

    lot = ServiceLot(
        category_id=category.id,
        name="Main Lot",
        slug="main-lot",
        description="Main",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("20.00"),
    )
    db_session.add(lot)
    await db_session.commit()

    return PersonalAssignmentsSeed(
        staff_user=staff_user,
        target_user_a=target_user_a,
        target_user_b=target_user_b,
        lot=lot,
    )


@pytest.mark.regression_catalog_promotions
async def test_create_assignment(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    personal_assignments_seed: PersonalAssignmentsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=personal_assignments_seed.staff_user.id,
    )
    now = now_utc()
    promotion_id = await _create_personal_promotion(
        client=client,
        headers=headers,
        lot_id=personal_assignments_seed.lot.id,
        user_id=personal_assignments_seed.target_user_a.id,
        assignment_expires_at=(now + timedelta(days=7)).isoformat(),
    )

    create_assignment_response = await client.post(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        json={
            "user_id": personal_assignments_seed.target_user_b.id,
            "expires_at": (now + timedelta(days=10)).isoformat(),
        },
    )
    assert create_assignment_response.status_code == 201
    assignment_data = _response_data(create_assignment_response.json())
    assert assignment_data["promotion_id"] == promotion_id
    assert assignment_data["user_id"] == personal_assignments_seed.target_user_b.id
    assert assignment_data["is_one_time"] is True
    assert assignment_data["expires_at"] is not None


async def test_reject_duplicate_assignment_for_same_user_and_promotion(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    personal_assignments_seed: PersonalAssignmentsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=personal_assignments_seed.staff_user.id,
    )
    now = now_utc()
    promotion_id = await _create_personal_promotion(
        client=client,
        headers=headers,
        lot_id=personal_assignments_seed.lot.id,
        user_id=personal_assignments_seed.target_user_a.id,
        assignment_expires_at=(now + timedelta(days=7)).isoformat(),
    )

    duplicate_assignment_response = await client.post(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        json={
            "user_id": personal_assignments_seed.target_user_a.id,
            "expires_at": (now + timedelta(days=5)).isoformat(),
        },
    )
    assert duplicate_assignment_response.status_code == 409
    assert _error_message(duplicate_assignment_response.json()) == (
        "Promotion assignment for this user already exists."
    )


@pytest.mark.regression_catalog_promotions
async def test_delete_assignment_and_reject_deleting_last_for_personal_promotion(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    personal_assignments_seed: PersonalAssignmentsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=personal_assignments_seed.staff_user.id,
    )
    now = now_utc()
    promotion_id = await _create_personal_promotion(
        client=client,
        headers=headers,
        lot_id=personal_assignments_seed.lot.id,
        user_id=personal_assignments_seed.target_user_a.id,
        assignment_expires_at=(now + timedelta(days=7)).isoformat(),
    )

    second_assignment_response = await client.post(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        json={
            "user_id": personal_assignments_seed.target_user_b.id,
            "expires_at": (now + timedelta(days=8)).isoformat(),
        },
    )
    assert second_assignment_response.status_code == 201
    second_assignment_id = _response_data(second_assignment_response.json())["id"]

    delete_second_response = await client.delete(
        (
            f"/api/v1/admin/promotions/{promotion_id}/assignments/"
            f"{second_assignment_id}"
        ),
        headers=headers,
    )
    assert delete_second_response.status_code == 200
    deleted_assignment = _response_data(delete_second_response.json())
    assert deleted_assignment["id"] == second_assignment_id

    remaining_assignments_response = await client.get(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
    )
    assert remaining_assignments_response.status_code == 200
    assignment_items = _response_items(remaining_assignments_response.json())
    assert len(assignment_items) == 1
    assert assignment_items[0]["user_id"] == personal_assignments_seed.target_user_a.id

    last_assignment_id = assignment_items[0]["id"]
    delete_last_response = await client.delete(
        f"/api/v1/admin/promotions/{promotion_id}/assignments/{last_assignment_id}",
        headers=headers,
    )
    assert delete_last_response.status_code == 400
    assert _error_message(delete_last_response.json()) == (
        "Cannot delete the last assignment for PERSONAL promotion."
    )


async def test_expired_assignment_behavior(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    personal_assignments_seed: PersonalAssignmentsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=personal_assignments_seed.staff_user.id,
    )
    now = now_utc()
    promotion_id = await _create_personal_promotion(
        client=client,
        headers=headers,
        lot_id=personal_assignments_seed.lot.id,
        user_id=personal_assignments_seed.target_user_a.id,
        assignment_expires_at=(now + timedelta(days=7)).isoformat(),
    )

    expired_assignment_response = await client.post(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        json={
            "user_id": personal_assignments_seed.target_user_b.id,
            "expires_at": (now - timedelta(days=1)).isoformat(),
        },
    )
    assert expired_assignment_response.status_code == 201

    active_assignments_response = await client.get(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        params={"state": "active"},
    )
    assert active_assignments_response.status_code == 200
    active_items = _response_items(active_assignments_response.json())
    assert len(active_items) == 1
    assert active_items[0]["user_id"] == personal_assignments_seed.target_user_a.id

    expired_assignments_response = await client.get(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        params={"state": "expired"},
    )
    assert expired_assignments_response.status_code == 200
    expired_items = _response_items(expired_assignments_response.json())
    assert len(expired_items) == 1
    assert expired_items[0]["user_id"] == personal_assignments_seed.target_user_b.id


async def test_one_time_assignment_used_behavior_if_supported(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    db_session: AsyncSession,
    personal_assignments_seed: PersonalAssignmentsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=personal_assignments_seed.staff_user.id,
    )
    now = now_utc()
    promotion_id = await _create_personal_promotion(
        client=client,
        headers=headers,
        lot_id=personal_assignments_seed.lot.id,
        user_id=personal_assignments_seed.target_user_a.id,
        assignment_expires_at=(now + timedelta(days=7)).isoformat(),
    )

    second_assignment_response = await client.post(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        json={
            "user_id": personal_assignments_seed.target_user_b.id,
            "expires_at": (now + timedelta(days=7)).isoformat(),
        },
    )
    assert second_assignment_response.status_code == 201

    order = Order(
        public_number="ORD-USED-1",
        status=OrderStatus.CREATED,
        execution_mode=ExecutionMode.SELF_PLAY,
        customer_user_id=personal_assignments_seed.target_user_b.id,
        service_lot_id=personal_assignments_seed.lot.id,
        selected_options_json=None,
        price_snapshot_json=None,
        internal_note=None,
        paid_at=None,
        paid_by_admin_id=None,
        accepted_at=None,
        in_progress_at=None,
        done_at=None,
        closed_at=None,
    )
    db_session.add(order)
    await db_session.flush()

    usage = PromotionUsage(
        promotion_id=promotion_id,
        user_id=personal_assignments_seed.target_user_b.id,
        order_id=order.id,
        applied_at=now,
        price_before_eur=Decimal("20.00"),
        discount_amount_eur=Decimal("3.00"),
        price_after_eur=Decimal("17.00"),
    )
    db_session.add(usage)
    await db_session.commit()

    used_assignments_response = await client.get(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        params={"state": "used"},
    )
    assert used_assignments_response.status_code == 200
    used_items = _response_items(used_assignments_response.json())
    assert len(used_items) == 1
    assert used_items[0]["user_id"] == personal_assignments_seed.target_user_b.id
    assert used_items[0]["is_one_time"] is True

    active_assignments_response = await client.get(
        f"/api/v1/admin/promotions/{promotion_id}/assignments",
        headers=headers,
        params={"state": "active"},
    )
    assert active_assignments_response.status_code == 200
    active_items = _response_items(active_assignments_response.json())
    assert len(active_items) == 1
    assert active_items[0]["user_id"] == personal_assignments_seed.target_user_a.id
    assert active_items[0]["is_one_time"] is True
