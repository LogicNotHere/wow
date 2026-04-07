from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from wow_shop.modules.auth.infrastructure.db.models import UserRole
from wow_shop.modules.auth.infrastructure.db.models import User, UserStatus
from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    LotOption,
    LotOptionInputType,
    LotOptionValue,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServiceLotStatus,
    ServicePage,
    ServicePageStatus,
)
from wow_shop.shared.utils.time import now_utc


@dataclass(slots=True)
class LotFlowsSeed:
    staff_user: User
    game: Game
    category: ServiceCategory
    lot_main: ServiceLot
    lot_compare: ServiceLot
    compare_active_option: LotOption
    compare_inactive_option: LotOption
    compare_active_value: LotOptionValue
    compare_inactive_value: LotOptionValue


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


@pytest_asyncio.fixture
async def lot_flows_seed(db_session: AsyncSession) -> LotFlowsSeed:
    staff_user = User(
        email="admin@example.com",
        password_hash=None,
        status=UserStatus.ACTIVE,
        role=UserRole.ADMIN,
    )
    db_session.add(staff_user)
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

    lot_main = ServiceLot(
        category_id=category.id,
        name="Main Lot",
        slug="main-lot",
        description="Main lot description",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("20.00"),
    )
    lot_compare = ServiceLot(
        category_id=category.id,
        name="Compare Lot",
        slug="compare-lot",
        description="Compare lot description",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("30.00"),
    )
    db_session.add_all([lot_main, lot_compare])
    await db_session.flush()

    compare_page = ServicePage(
        lot_id=lot_compare.id,
        status=ServicePageStatus.PUBLISHED,
        title="Compare Page",
        meta_json={"k": "v"},
        published_at=now_utc(),
    )
    db_session.add(compare_page)
    await db_session.flush()

    compare_active_option = LotOption(
        lot_id=lot_compare.id,
        label="Region",
        code="region",
        input_type=LotOptionInputType.SELECT,
        is_required=True,
        sort_order=0,
        is_active=True,
        depends_on_option_id=None,
        depends_on_value_id=None,
    )
    compare_inactive_option = LotOption(
        lot_id=lot_compare.id,
        label="Legacy",
        code="legacy",
        input_type=LotOptionInputType.CHECKBOX,
        is_required=False,
        sort_order=1,
        is_active=False,
        depends_on_option_id=None,
        depends_on_value_id=None,
    )
    db_session.add_all([compare_active_option, compare_inactive_option])
    await db_session.flush()

    compare_active_value = LotOptionValue(
        option_id=compare_active_option.id,
        label="EU",
        code="eu",
        description=None,
        price_value=Decimal("0.00"),
        sort_order=0,
        is_default=True,
        is_active=True,
    )
    compare_inactive_value = LotOptionValue(
        option_id=compare_active_option.id,
        label="US Legacy",
        code="us-legacy",
        description=None,
        price_value=Decimal("3.00"),
        sort_order=1,
        is_default=False,
        is_active=False,
    )
    db_session.add_all([compare_active_value, compare_inactive_value])
    await db_session.commit()

    return LotFlowsSeed(
        staff_user=staff_user,
        game=game,
        category=category,
        lot_main=lot_main,
        lot_compare=lot_compare,
        compare_active_option=compare_active_option,
        compare_inactive_option=compare_inactive_option,
        compare_active_value=compare_active_value,
        compare_inactive_value=compare_inactive_value,
    )


async def test_staff_lot_option_create_update_reorder_delete_with_dependencies(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    lot_flows_seed: LotFlowsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=lot_flows_seed.staff_user.id,
    )

    create_region_response = await client.post(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options",
        headers=headers,
        json={
            "label": "Region",
            "code": "region",
            "input_type": "select",
            "is_required": True,
            "sort_order": 10,
            "is_active": True,
            "depends_on_option_id": None,
            "depends_on_value_id": None,
        },
    )
    assert create_region_response.status_code == 201
    region_option = _response_data(create_region_response.json())
    region_option_id = region_option["id"]
    assert region_option["code"] == "region"
    assert region_option["sort_order"] == 10

    create_region_eu_response = await client.post(
        (
            f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/"
            f"options/{region_option_id}/values"
        ),
        headers=headers,
        json={
            "label": "EU",
            "code": "eu",
            "description": "Europe",
            "price_value": "0.00",
            "sort_order": 5,
            "is_default": True,
            "is_active": True,
        },
    )
    assert create_region_eu_response.status_code == 201
    get_region_option_response = await client.get(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{region_option_id}",
        headers=headers,
    )
    assert get_region_option_response.status_code == 200
    region_option_data = _response_data(get_region_option_response.json())
    assert len(region_option_data["values"]) == 1
    region_eu_id = region_option_data["values"][0]["id"]

    create_region_us_response = await client.post(
        (
            f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/"
            f"options/{region_option_id}/values"
        ),
        headers=headers,
        json={
            "label": "US",
            "code": "us",
            "description": "United States",
            "price_value": "1.50",
            "sort_order": 10,
            "is_default": False,
            "is_active": True,
        },
    )
    assert create_region_us_response.status_code == 201
    get_region_option_response = await client.get(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{region_option_id}",
        headers=headers,
    )
    assert get_region_option_response.status_code == 200
    region_option_data = _response_data(get_region_option_response.json())
    value_ids = [value["id"] for value in region_option_data["values"]]
    assert len(value_ids) == 2
    region_us_id = next(value_id for value_id in value_ids if value_id != region_eu_id)

    invalid_dependency_response = await client.post(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options",
        headers=headers,
        json={
            "label": "Mode Invalid",
            "code": "mode-invalid",
            "input_type": "radio",
            "is_required": False,
            "sort_order": 0,
            "is_active": True,
            "depends_on_option_id": region_option_id,
        },
    )
    assert invalid_dependency_response.status_code == 400
    assert invalid_dependency_response.json()["status"] == "error"

    create_mode_response = await client.post(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options",
        headers=headers,
        json={
            "label": "Mode",
            "code": "mode",
            "input_type": "radio",
            "is_required": False,
            "sort_order": 0,
            "is_active": True,
            "depends_on_option_id": region_option_id,
            "depends_on_value_id": region_eu_id,
        },
    )
    assert create_mode_response.status_code == 201
    mode_option = _response_data(create_mode_response.json())
    mode_option_id = mode_option["id"]
    assert mode_option["depends_on_option_id"] == region_option_id
    assert mode_option["depends_on_value_id"] == region_eu_id

    update_mode_response = await client.patch(
        (
            f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/"
            f"options/{mode_option_id}"
        ),
        headers=headers,
        json={
            "label": "Mode Updated",
            "is_active": False,
            "depends_on_option_id": region_option_id,
            "depends_on_value_id": region_us_id,
        },
    )
    assert update_mode_response.status_code == 200
    updated_mode = _response_data(update_mode_response.json())
    assert updated_mode["label"] == "Mode Updated"
    assert updated_mode["is_active"] is False
    assert updated_mode["depends_on_option_id"] == region_option_id
    assert updated_mode["depends_on_value_id"] == region_us_id

    reorder_options_response = await client.patch(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/reorder",
        headers=headers,
        json={"ids": [region_option_id, mode_option_id]},
    )
    assert reorder_options_response.status_code == 200
    reordered_options = _response_items(reorder_options_response.json())
    assert [item["id"] for item in reordered_options] == [
        region_option_id,
        mode_option_id,
    ]
    assert [item["sort_order"] for item in reordered_options] == [0, 1]

    delete_option_response = await client.delete(
        (
            f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/"
            f"options/{mode_option_id}"
        ),
        headers=headers,
    )
    assert delete_option_response.status_code == 200
    remaining_options = _response_items(delete_option_response.json())
    assert [item["id"] for item in remaining_options] == [region_option_id]


async def test_staff_option_value_create_update_reorder_delete(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    lot_flows_seed: LotFlowsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=lot_flows_seed.staff_user.id,
    )

    create_option_response = await client.post(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options",
        headers=headers,
        json={
            "label": "Difficulty",
            "code": "difficulty",
            "input_type": "select",
            "is_required": True,
            "sort_order": 0,
            "is_active": True,
            "depends_on_option_id": None,
            "depends_on_value_id": None,
        },
    )
    assert create_option_response.status_code == 201
    option_data = _response_data(create_option_response.json())
    option_id = option_data["id"]

    create_bronze_response = await client.post(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{option_id}/values",
        headers=headers,
        json={
            "label": "Bronze",
            "code": "bronze",
            "description": "Bronze rank",
            "price_value": "2.00",
            "sort_order": 10,
            "is_default": True,
            "is_active": True,
        },
    )
    assert create_bronze_response.status_code == 201
    get_option_response = await client.get(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{option_id}",
        headers=headers,
    )
    assert get_option_response.status_code == 200
    option_data = _response_data(get_option_response.json())
    assert len(option_data["values"]) == 1
    bronze_value_id = option_data["values"][0]["id"]

    create_silver_response = await client.post(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{option_id}/values",
        headers=headers,
        json={
            "label": "Silver",
            "code": "silver",
            "description": "Silver rank",
            "price_value": "4.00",
            "sort_order": 0,
            "is_default": False,
            "is_active": True,
        },
    )
    assert create_silver_response.status_code == 201
    get_option_response = await client.get(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{option_id}",
        headers=headers,
    )
    assert get_option_response.status_code == 200
    option_data = _response_data(get_option_response.json())
    value_ids = [value["id"] for value in option_data["values"]]
    assert len(value_ids) == 2
    silver_value_id = next(value_id for value_id in value_ids if value_id != bronze_value_id)

    invalid_patch_response = await client.patch(
        (
            f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/"
            f"options/{option_id}/values/{bronze_value_id}"
        ),
        headers=headers,
        json={"sort_order": 99},
    )
    assert invalid_patch_response.status_code == 422

    update_bronze_response = await client.patch(
        (
            f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/"
            f"options/{option_id}/values/{bronze_value_id}"
        ),
        headers=headers,
        json={
            "label": "Bronze Updated",
            "price_value": "3.50",
            "is_active": False,
        },
    )
    assert update_bronze_response.status_code == 200
    option_data = _response_data(update_bronze_response.json())
    bronze_value = next(
        value for value in option_data["values"] if value["id"] == bronze_value_id
    )
    assert bronze_value["label"] == "Bronze Updated"
    assert bronze_value["price_value"] == "3.50"
    assert bronze_value["is_active"] is False

    reorder_values_response = await client.patch(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{option_id}/values/reorder",
        headers=headers,
        json={"ids": [bronze_value_id, silver_value_id]},
    )
    assert reorder_values_response.status_code == 200
    option_data = _response_data(reorder_values_response.json())
    assert [value["id"] for value in option_data["values"]] == [
        bronze_value_id,
        silver_value_id,
    ]
    assert [value["sort_order"] for value in option_data["values"]] == [0, 1]

    delete_value_response = await client.delete(
        (
            f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/"
            f"options/{option_id}/values/{silver_value_id}"
        ),
        headers=headers,
    )
    assert delete_value_response.status_code == 200
    get_option_response = await client.get(
        f"/api/v1/admin/lots/{lot_flows_seed.lot_main.id}/options/{option_id}",
        headers=headers,
    )
    assert get_option_response.status_code == 200
    option_data = _response_data(get_option_response.json())
    assert [value["id"] for value in option_data["values"]] == [bronze_value_id]


async def test_staff_lot_page_upsert_get_status_and_blocks_flows(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    lot_flows_seed: LotFlowsSeed,
) -> None:
    headers = auth_headers(
        role=UserRole.ADMIN,
        user_id=lot_flows_seed.staff_user.id,
    )
    lot_id = lot_flows_seed.lot_main.id

    create_page_response = await client.put(
        f"/api/v1/admin/lots/{lot_id}/page",
        headers=headers,
        json={"title": "Main Draft", "meta_json": {"seo": "draft"}},
    )
    assert create_page_response.status_code == 200
    page_data = _response_data(create_page_response.json())
    assert page_data["status"] == "draft"
    assert page_data["title"] == "Main Draft"
    assert page_data["meta_json"] == {"seo": "draft"}
    assert page_data["published_at"] is None
    assert page_data["blocks"] == []

    get_page_response = await client.get(
        f"/api/v1/admin/lots/{lot_id}/page",
        headers=headers,
    )
    assert get_page_response.status_code == 200
    page_data = _response_data(get_page_response.json())
    assert page_data["title"] == "Main Draft"

    publish_page_response = await client.patch(
        f"/api/v1/admin/lots/{lot_id}/page/status",
        headers=headers,
        json={"status": "published"},
    )
    assert publish_page_response.status_code == 200
    page_data = _response_data(publish_page_response.json())
    assert page_data["status"] == "published"
    assert page_data["published_at"] is not None

    update_page_response = await client.put(
        f"/api/v1/admin/lots/{lot_id}/page",
        headers=headers,
        json={"title": "Main Updated", "meta_json": {"seo": "updated"}},
    )
    assert update_page_response.status_code == 200
    page_data = _response_data(update_page_response.json())
    assert page_data["status"] == "draft"
    assert page_data["published_at"] is None
    assert page_data["title"] == "Main Updated"

    create_first_block_response = await client.post(
        f"/api/v1/admin/lots/{lot_id}/page/blocks",
        headers=headers,
        json={"type": "text", "payload_json": {"text": "A"}},
    )
    assert create_first_block_response.status_code == 200
    get_page_after_first_block_response = await client.get(
        f"/api/v1/admin/lots/{lot_id}/page",
        headers=headers,
    )
    assert get_page_after_first_block_response.status_code == 200
    page_data = _response_data(get_page_after_first_block_response.json())
    assert len(page_data["blocks"]) == 1
    first_block_id = page_data["blocks"][0]["id"]

    create_second_block_response = await client.post(
        f"/api/v1/admin/lots/{lot_id}/page/blocks",
        headers=headers,
        json={"position": 1, "type": "cta", "payload_json": {"text": "B"}},
    )
    assert create_second_block_response.status_code == 200
    get_page_after_second_block_response = await client.get(
        f"/api/v1/admin/lots/{lot_id}/page",
        headers=headers,
    )
    assert get_page_after_second_block_response.status_code == 200
    page_data = _response_data(get_page_after_second_block_response.json())
    second_block_id = page_data["blocks"][1]["id"]
    assert [block["id"] for block in page_data["blocks"]] == [
        first_block_id,
        second_block_id,
    ]
    assert [block["position"] for block in page_data["blocks"]] == [0, 1]

    republish_page_response = await client.patch(
        f"/api/v1/admin/lots/{lot_id}/page/status",
        headers=headers,
        json={"status": "published"},
    )
    assert republish_page_response.status_code == 200
    assert _response_data(republish_page_response.json())["status"] == "published"

    invalid_block_patch_response = await client.patch(
        f"/api/v1/admin/lots/{lot_id}/page/blocks/{first_block_id}",
        headers=headers,
        json={"position": 10},
    )
    assert invalid_block_patch_response.status_code == 422

    update_block_response = await client.patch(
        f"/api/v1/admin/lots/{lot_id}/page/blocks/{first_block_id}",
        headers=headers,
        json={"payload_json": {"text": "A updated"}},
    )
    assert update_block_response.status_code == 200
    page_data = _response_data(update_block_response.json())
    assert page_data["status"] == "draft"
    assert page_data["published_at"] is None
    updated_block = next(
        block for block in page_data["blocks"] if block["id"] == first_block_id
    )
    assert updated_block["payload_json"] == {"text": "A updated"}

    reorder_blocks_response = await client.patch(
        f"/api/v1/admin/lots/{lot_id}/page/blocks/reorder",
        headers=headers,
        json={"ids": [second_block_id, first_block_id]},
    )
    assert reorder_blocks_response.status_code == 200
    page_data = _response_data(reorder_blocks_response.json())
    assert [block["id"] for block in page_data["blocks"]] == [
        second_block_id,
        first_block_id,
    ]
    assert [block["position"] for block in page_data["blocks"]] == [0, 1]

    delete_block_response = await client.delete(
        f"/api/v1/admin/lots/{lot_id}/page/blocks/{second_block_id}",
        headers=headers,
    )
    assert delete_block_response.status_code == 200
    page_after_delete_response = await client.get(
        f"/api/v1/admin/lots/{lot_id}/page",
        headers=headers,
    )
    assert page_after_delete_response.status_code == 200
    page_data = _response_data(page_after_delete_response.json())
    assert [block["id"] for block in page_data["blocks"]] == [first_block_id]


async def test_public_vs_staff_detail_for_same_lot_options_visibility(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    lot_flows_seed: LotFlowsSeed,
) -> None:
    public_response = await client.get(
        "/api/v1/lots/wow/mythic-plus/compare-lot",
    )
    staff_response = await client.get(
        "/api/v1/admin/lots/by-slug/wow/mythic-plus/compare-lot",
        headers=auth_headers(
            role=UserRole.ADMIN,
            user_id=lot_flows_seed.staff_user.id,
        ),
    )

    assert public_response.status_code == 200
    assert staff_response.status_code == 200

    public_options = _response_data(public_response.json())["options"]
    staff_options = _response_data(staff_response.json())["options"]

    assert {item["id"] for item in public_options} == {
        lot_flows_seed.compare_active_option.id
    }
    assert {item["id"] for item in staff_options} == {
        lot_flows_seed.compare_active_option.id,
        lot_flows_seed.compare_inactive_option.id,
    }

    public_active_option = next(
        item
        for item in public_options
        if item["id"] == lot_flows_seed.compare_active_option.id
    )
    staff_active_option = next(
        item
        for item in staff_options
        if item["id"] == lot_flows_seed.compare_active_option.id
    )
    assert [value["id"] for value in public_active_option["values"]] == [
        lot_flows_seed.compare_active_value.id
    ]
    assert {value["id"] for value in staff_active_option["values"]} == {
        lot_flows_seed.compare_active_value.id,
        lot_flows_seed.compare_inactive_value.id,
    }
