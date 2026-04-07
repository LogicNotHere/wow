from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from wow_shop.modules.catalog.infrastructure.db.models import (
    Game,
    GameStatus,
    ServiceCategory,
    ServiceCategoryStatus,
    ServiceLot,
    ServiceLotStatus,
    ServicePage,
    ServicePageStatus,
)
from wow_shop.shared.utils.time import now_utc


@dataclass(slots=True)
class PublicLotsSeed:
    game_wow: Game
    game_classic: Game
    game_inactive: Game
    category_mplus: ServiceCategory
    category_raids: ServiceCategory
    category_pvp: ServiceCategory
    category_hidden: ServiceCategory
    category_in_inactive_game: ServiceCategory
    lot_mplus_1: ServiceLot
    lot_mplus_2: ServiceLot
    lot_raids_1: ServiceLot
    lot_pvp_1: ServiceLot
    lot_hidden_status: ServiceLot
    lot_unpublished_page: ServiceLot
    lot_in_hidden_category: ServiceLot
    lot_in_inactive_game: ServiceLot


async def _create_lot_with_page(
    db_session: AsyncSession,
    *,
    category: ServiceCategory,
    slug: str,
    status: ServiceLotStatus = ServiceLotStatus.ACTIVE,
    page_status: ServicePageStatus = ServicePageStatus.PUBLISHED,
) -> ServiceLot:
    lot = ServiceLot(
        category_id=category.id,
        name=slug.replace("-", " ").title(),
        slug=slug,
        description=f"{slug} description",
        status=status,
        base_price_eur=Decimal("10.00"),
    )
    db_session.add(lot)
    await db_session.flush()

    page = ServicePage(
        lot_id=lot.id,
        status=page_status,
        title=f"{slug} page",
        meta_json=None,
        published_at=(now_utc() if page_status == ServicePageStatus.PUBLISHED else None),
    )
    db_session.add(page)
    await db_session.flush()
    return lot


@pytest_asyncio.fixture
async def public_lots_seed(db_session: AsyncSession) -> PublicLotsSeed:
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
    game_inactive = Game(
        name="Old Game",
        slug="old-game",
        status=GameStatus.INACTIVE,
        sort_order=3,
    )
    db_session.add_all([game_wow, game_classic, game_inactive])
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
    category_hidden = ServiceCategory(
        game_id=game_wow.id,
        name="Hidden",
        slug="hidden",
        parent_id=None,
        status=ServiceCategoryStatus.INACTIVE,
        sort_order=3,
    )
    category_pvp = ServiceCategory(
        game_id=game_classic.id,
        name="PvP",
        slug="pvp",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    category_in_inactive_game = ServiceCategory(
        game_id=game_inactive.id,
        name="Legacy",
        slug="legacy",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    db_session.add_all(
        [
            category_mplus,
            category_raids,
            category_hidden,
            category_pvp,
            category_in_inactive_game,
        ]
    )
    await db_session.flush()

    lot_mplus_1 = await _create_lot_with_page(
        db_session,
        category=category_mplus,
        slug="mplus-lot-1",
    )
    lot_mplus_2 = await _create_lot_with_page(
        db_session,
        category=category_mplus,
        slug="mplus-lot-2",
    )
    lot_raids_1 = await _create_lot_with_page(
        db_session,
        category=category_raids,
        slug="raids-lot-1",
    )
    lot_pvp_1 = await _create_lot_with_page(
        db_session,
        category=category_pvp,
        slug="pvp-lot-1",
    )
    lot_hidden_status = await _create_lot_with_page(
        db_session,
        category=category_mplus,
        slug="hidden-status-lot",
        status=ServiceLotStatus.INACTIVE,
    )
    lot_unpublished_page = await _create_lot_with_page(
        db_session,
        category=category_mplus,
        slug="unpublished-page-lot",
        page_status=ServicePageStatus.DRAFT,
    )
    lot_in_hidden_category = await _create_lot_with_page(
        db_session,
        category=category_hidden,
        slug="hidden-category-lot",
    )
    lot_in_inactive_game = await _create_lot_with_page(
        db_session,
        category=category_in_inactive_game,
        slug="inactive-game-lot",
    )
    await db_session.commit()

    return PublicLotsSeed(
        game_wow=game_wow,
        game_classic=game_classic,
        game_inactive=game_inactive,
        category_mplus=category_mplus,
        category_raids=category_raids,
        category_pvp=category_pvp,
        category_hidden=category_hidden,
        category_in_inactive_game=category_in_inactive_game,
        lot_mplus_1=lot_mplus_1,
        lot_mplus_2=lot_mplus_2,
        lot_raids_1=lot_raids_1,
        lot_pvp_1=lot_pvp_1,
        lot_hidden_status=lot_hidden_status,
        lot_unpublished_page=lot_unpublished_page,
        lot_in_hidden_category=lot_in_hidden_category,
        lot_in_inactive_game=lot_in_inactive_game,
    )


def _response_items(response: dict) -> list[dict]:
    data = response["data"]
    assert data is not None
    items = data.get("items")
    assert isinstance(items, list)
    return items


async def test_public_lots_list_filter_by_game_slug(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get("/api/v1/lots/", params={"game_slug": "wow"})

    assert response.status_code == 200
    items = _response_items(response.json())
    assert {item["id"] for item in items} == {
        public_lots_seed.lot_mplus_1.id,
        public_lots_seed.lot_mplus_2.id,
        public_lots_seed.lot_raids_1.id,
    }


@pytest.mark.regression_catalog_promotions
async def test_public_lots_list_filter_by_game_and_category(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params={
            "game_slug": "wow",
            "category_slug": "mythic-plus",
        },
    )

    assert response.status_code == 200
    items = _response_items(response.json())
    assert [item["id"] for item in items] == [
        public_lots_seed.lot_mplus_1.id,
        public_lots_seed.lot_mplus_2.id,
    ]


async def test_public_lots_list_filter_by_lot_ids(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params=[
            ("lot_ids", public_lots_seed.lot_mplus_1.id),
            ("lot_ids", public_lots_seed.lot_pvp_1.id),
            ("lot_ids", public_lots_seed.lot_hidden_status.id),
        ],
    )

    assert response.status_code == 200
    items = _response_items(response.json())
    assert {item["id"] for item in items} == {
        public_lots_seed.lot_mplus_1.id,
        public_lots_seed.lot_pvp_1.id,
    }


async def test_public_lots_list_lot_ids_from_different_games_and_categories(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params=[
            ("lot_ids", public_lots_seed.lot_mplus_2.id),
            ("lot_ids", public_lots_seed.lot_raids_1.id),
            ("lot_ids", public_lots_seed.lot_pvp_1.id),
        ],
    )

    assert response.status_code == 200
    items = _response_items(response.json())
    assert {item["id"] for item in items} == {
        public_lots_seed.lot_mplus_2.id,
        public_lots_seed.lot_raids_1.id,
        public_lots_seed.lot_pvp_1.id,
    }


async def test_public_lots_list_intersection_lot_ids_with_scope(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params=[
            ("game_slug", "wow"),
            ("category_slug", "mythic-plus"),
            ("lot_ids", public_lots_seed.lot_mplus_1.id),
            ("lot_ids", public_lots_seed.lot_raids_1.id),
            ("lot_ids", public_lots_seed.lot_pvp_1.id),
        ],
    )

    assert response.status_code == 200
    items = _response_items(response.json())
    assert [item["id"] for item in items] == [public_lots_seed.lot_mplus_1.id]


async def test_public_lots_list_limit_and_offset(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params={
            "game_slug": "wow",
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200
    items = _response_items(response.json())
    assert len(items) == 1
    assert items[0]["id"] == public_lots_seed.lot_mplus_2.id


async def test_public_lots_list_invalid_game_slug(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/lots/", params={"game_slug": "BAD!"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"


async def test_public_lots_list_invalid_category_slug(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params={
            "game_slug": "wow",
            "category_slug": "BAD!",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"


async def test_public_lots_list_unknown_game_slug_returns_404(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params={"game_slug": "not-exists"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"


async def test_public_lots_list_unknown_category_slug_returns_404(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params={
            "game_slug": "wow",
            "category_slug": "not-exists",
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"


@pytest.mark.regression_catalog_promotions
async def test_public_lot_detail_happy_path(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get("/api/v1/lots/wow/mythic-plus/mplus-lot-1")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["slug"] == "mplus-lot-1"


async def test_public_lot_detail_not_found(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get("/api/v1/lots/wow/mythic-plus/not-exists")

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"


async def test_public_lot_detail_hidden_or_unpublished_excluded(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    hidden_status_response = await client.get(
        "/api/v1/lots/wow/mythic-plus/hidden-status-lot"
    )
    unpublished_response = await client.get(
        "/api/v1/lots/wow/mythic-plus/unpublished-page-lot"
    )

    assert hidden_status_response.status_code == 404
    assert unpublished_response.status_code == 404


async def test_public_visibility_excludes_inactive_category_and_game(
    client: AsyncClient,
    public_lots_seed: PublicLotsSeed,
) -> None:
    response = await client.get(
        "/api/v1/lots/",
        params=[
            ("lot_ids", public_lots_seed.lot_in_hidden_category.id),
            ("lot_ids", public_lots_seed.lot_in_inactive_game.id),
            ("lot_ids", public_lots_seed.lot_mplus_1.id),
        ],
    )

    assert response.status_code == 200
    items = _response_items(response.json())
    assert [item["id"] for item in items] == [public_lots_seed.lot_mplus_1.id]
