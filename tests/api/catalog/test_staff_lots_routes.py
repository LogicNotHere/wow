from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from wow_shop.modules.auth.infrastructure.db.models import UserRole
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
class StaffLotsSeed:
    game_wow: Game
    game_classic: Game
    category_mplus: ServiceCategory
    category_raids: ServiceCategory
    category_pvp: ServiceCategory
    lot_alpha: ServiceLot
    lot_bravo_unpublished: ServiceLot
    lot_charlie: ServiceLot
    lot_delta_inactive: ServiceLot
    active_option: LotOption
    inactive_option: LotOption
    active_value: LotOptionValue
    inactive_value: LotOptionValue


async def _create_lot_with_page(
    db_session: AsyncSession,
    *,
    category: ServiceCategory,
    name: str,
    slug: str,
    status: ServiceLotStatus = ServiceLotStatus.ACTIVE,
    page_status: ServicePageStatus = ServicePageStatus.PUBLISHED,
) -> ServiceLot:
    lot = ServiceLot(
        category_id=category.id,
        name=name,
        slug=slug,
        description=f"{slug} description",
        status=status,
        base_price_eur=Decimal("25.00"),
    )
    db_session.add(lot)
    await db_session.flush()

    page = ServicePage(
        lot_id=lot.id,
        status=page_status,
        title=f"{name} page",
        meta_json=None,
        published_at=(
            now_utc()
            if page_status == ServicePageStatus.PUBLISHED
            else None
        ),
    )
    db_session.add(page)
    await db_session.flush()
    return lot


@pytest_asyncio.fixture
async def staff_lots_seed(db_session: AsyncSession) -> StaffLotsSeed:
    game_wow = Game(
        name="World of Warcraft",
        slug="wow",
        status=GameStatus.ACTIVE,
        sort_order=1,
    )
    game_classic = Game(
        name="Classic",
        slug="classic",
        status=GameStatus.ACTIVE,
        sort_order=2,
    )
    db_session.add_all([game_wow, game_classic])
    await db_session.flush()

    category_mplus = ServiceCategory(
        game_id=game_wow.id,
        name="Mythic Plus",
        slug="mythic-plus",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    category_raids = ServiceCategory(
        game_id=game_wow.id,
        name="Raids",
        slug="raids",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=2,
    )
    category_pvp = ServiceCategory(
        game_id=game_classic.id,
        name="PvP",
        slug="pvp",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    db_session.add_all([category_mplus, category_raids, category_pvp])
    await db_session.flush()

    lot_alpha = await _create_lot_with_page(
        db_session,
        category=category_mplus,
        name="Alpha Lot",
        slug="alpha-lot",
        status=ServiceLotStatus.ACTIVE,
        page_status=ServicePageStatus.PUBLISHED,
    )
    lot_bravo_unpublished = await _create_lot_with_page(
        db_session,
        category=category_raids,
        name="Bravo Lot",
        slug="bravo-lot",
        status=ServiceLotStatus.ACTIVE,
        page_status=ServicePageStatus.DRAFT,
    )
    lot_charlie = await _create_lot_with_page(
        db_session,
        category=category_pvp,
        name="Charlie Lot",
        slug="charlie-lot",
        status=ServiceLotStatus.DRAFT,
        page_status=ServicePageStatus.PUBLISHED,
    )
    lot_delta_inactive = await _create_lot_with_page(
        db_session,
        category=category_mplus,
        name="Delta Lot",
        slug="delta-lot",
        status=ServiceLotStatus.INACTIVE,
        page_status=ServicePageStatus.PUBLISHED,
    )

    active_option = LotOption(
        lot_id=lot_alpha.id,
        label="Region",
        code="region",
        input_type=LotOptionInputType.SELECT,
        is_required=True,
        sort_order=10,
        is_active=True,
        depends_on_option_id=None,
        depends_on_value_id=None,
    )
    inactive_option = LotOption(
        lot_id=lot_alpha.id,
        label="Legacy Mode",
        code="legacy-mode",
        input_type=LotOptionInputType.CHECKBOX,
        is_required=False,
        sort_order=20,
        is_active=False,
        depends_on_option_id=None,
        depends_on_value_id=None,
    )
    db_session.add_all([active_option, inactive_option])
    await db_session.flush()

    active_value = LotOptionValue(
        option_id=active_option.id,
        label="EU",
        code="eu",
        description=None,
        price_value=Decimal("0.00"),
        sort_order=0,
        is_default=True,
        is_active=True,
    )
    inactive_value = LotOptionValue(
        option_id=active_option.id,
        label="US Legacy",
        code="us-legacy",
        description=None,
        price_value=Decimal("2.00"),
        sort_order=1,
        is_default=False,
        is_active=False,
    )
    db_session.add_all([active_value, inactive_value])
    await db_session.commit()

    return StaffLotsSeed(
        game_wow=game_wow,
        game_classic=game_classic,
        category_mplus=category_mplus,
        category_raids=category_raids,
        category_pvp=category_pvp,
        lot_alpha=lot_alpha,
        lot_bravo_unpublished=lot_bravo_unpublished,
        lot_charlie=lot_charlie,
        lot_delta_inactive=lot_delta_inactive,
        active_option=active_option,
        inactive_option=inactive_option,
        active_value=active_value,
        inactive_value=inactive_value,
    )


def _response_items(response: dict) -> list[dict]:
    data = response["data"]
    assert data is not None
    items = data.get("items")
    assert isinstance(items, list)
    return items


@pytest.mark.regression_catalog_promotions
async def test_staff_lots_list_filters(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    staff_lots_seed: StaffLotsSeed,
) -> None:
    response_by_status = await client.get(
        "/api/v1/admin/lots/",
        headers=auth_headers(role=UserRole.ADMIN),
        params={"status": "active"},
    )
    assert response_by_status.status_code == 200
    items = _response_items(response_by_status.json())
    assert {item["id"] for item in items} == {
        staff_lots_seed.lot_alpha.id,
        staff_lots_seed.lot_bravo_unpublished.id,
    }

    response_by_game = await client.get(
        "/api/v1/admin/lots/",
        headers=auth_headers(role=UserRole.ADMIN),
        params={"game_id": staff_lots_seed.game_wow.id},
    )
    assert response_by_game.status_code == 200
    items = _response_items(response_by_game.json())
    assert {item["id"] for item in items} == {
        staff_lots_seed.lot_alpha.id,
        staff_lots_seed.lot_bravo_unpublished.id,
        staff_lots_seed.lot_delta_inactive.id,
    }

    response_by_category_and_search = await client.get(
        "/api/v1/admin/lots/",
        headers=auth_headers(role=UserRole.ADMIN),
        params={
            "category_id": staff_lots_seed.category_mplus.id,
            "search": "alpha",
        },
    )
    assert response_by_category_and_search.status_code == 200
    items = _response_items(response_by_category_and_search.json())
    assert [item["id"] for item in items] == [staff_lots_seed.lot_alpha.id]


async def test_staff_lots_list_order_by_and_pagination(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    staff_lots_seed: StaffLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/admin/lots/",
        headers=auth_headers(role=UserRole.ADMIN),
        params={
            "order_by": "name_asc",
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200
    items = _response_items(response.json())
    assert [item["name"] for item in items] == [
        "Bravo Lot",
        "Charlie Lot",
    ]


@pytest.mark.regression_catalog_promotions
async def test_staff_lot_detail_by_slug_happy_path_and_inactive_options_visible(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    staff_lots_seed: StaffLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/admin/lots/by-slug/wow/mythic-plus/alpha-lot",
        headers=auth_headers(role=UserRole.ADMIN),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["slug"] == "alpha-lot"

    option_ids = {option["id"] for option in data["options"]}
    assert option_ids == {
        staff_lots_seed.active_option.id,
        staff_lots_seed.inactive_option.id,
    }

    active_option_response = next(
        option
        for option in data["options"]
        if option["id"] == staff_lots_seed.active_option.id
    )
    value_ids = {value["id"] for value in active_option_response["values"]}
    assert value_ids == {
        staff_lots_seed.active_value.id,
        staff_lots_seed.inactive_value.id,
    }


async def test_staff_lot_detail_by_slug_not_found(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    staff_lots_seed: StaffLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/admin/lots/by-slug/wow/mythic-plus/not-exists",
        headers=auth_headers(role=UserRole.ADMIN),
    )

    assert response.status_code == 404
    assert response.json()["status"] == "error"


async def test_public_vs_staff_lot_detail_same_lot_behavior_differs(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    staff_lots_seed: StaffLotsSeed,
) -> None:
    public_response = await client.get("/api/v1/lots/wow/mythic-plus/alpha-lot")
    staff_response = await client.get(
        "/api/v1/admin/lots/by-slug/wow/mythic-plus/alpha-lot",
        headers=auth_headers(role=UserRole.ADMIN),
    )

    assert public_response.status_code == 200
    assert staff_response.status_code == 200

    public_options = public_response.json()["data"]["options"]
    staff_options = staff_response.json()["data"]["options"]

    assert {option["id"] for option in public_options} == {
        staff_lots_seed.active_option.id
    }
    assert {option["id"] for option in staff_options} == {
        staff_lots_seed.active_option.id,
        staff_lots_seed.inactive_option.id,
    }

    public_active_option = next(
        option
        for option in public_options
        if option["id"] == staff_lots_seed.active_option.id
    )
    staff_active_option = next(
        option
        for option in staff_options
        if option["id"] == staff_lots_seed.active_option.id
    )
    assert [value["id"] for value in public_active_option["values"]] == [
        staff_lots_seed.active_value.id
    ]
    assert {value["id"] for value in staff_active_option["values"]} == {
        staff_lots_seed.active_value.id,
        staff_lots_seed.inactive_value.id,
    }
