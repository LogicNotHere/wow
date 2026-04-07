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
    ServicePage,
    ServicePageStatus,
)
from wow_shop.modules.pricing.infrastructure.db.models import (
    PersonalPromotionAssignment,
    Promotion,
    PromotionAudience,
    PromotionBadgeTag,
    PromotionDiscountType,
)
from wow_shop.shared.utils.time import now_utc


@dataclass(slots=True)
class PublicPromotionsSeed:
    customer_user: User
    category_visible_primary: ServiceCategory
    category_visible_secondary: ServiceCategory
    lot_visible_main: ServiceLot
    lot_visible_badge: ServiceLot
    public_lot_discount_id: int
    public_lot_badge_hot_id: int
    public_category_badge_hot_id: int
    public_category_discount_invalid_id: int
    personal_lot_discount_id: int
    personal_category_discount_id: int
    hidden_public_lot_badge_id: int
    hidden_public_category_badge_id: int


def _response_data(response: dict[str, Any]) -> dict[str, Any]:
    assert response["status"] == "success"
    data = response["data"]
    assert isinstance(data, dict)
    return data


def _response_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    items = _response_data(response).get("items")
    assert isinstance(items, list)
    return items


def _item_ids(items: list[dict[str, Any]]) -> set[int]:
    return {item["promotion_id"] for item in items}


@pytest_asyncio.fixture
async def public_promotions_seed(
    db_session: AsyncSession,
) -> PublicPromotionsSeed:
    customer_user = User(
        email="customer@example.com",
        password_hash=None,
        status=UserStatus.ACTIVE,
        role=UserRole.CUSTOMER,
    )
    db_session.add(customer_user)
    await db_session.flush()

    game_visible = Game(
        name="World of Warcraft",
        slug="wow",
        status=GameStatus.ACTIVE,
        sort_order=1,
    )
    game_hidden = Game(
        name="Hidden Game",
        slug="hidden-game",
        status=GameStatus.INACTIVE,
        sort_order=2,
    )
    db_session.add_all([game_visible, game_hidden])
    await db_session.flush()

    category_visible_primary = ServiceCategory(
        game_id=game_visible.id,
        name="Mythic Plus",
        slug="mythic-plus",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    category_visible_secondary = ServiceCategory(
        game_id=game_visible.id,
        name="Raids",
        slug="raids",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=2,
    )
    category_hidden_inactive = ServiceCategory(
        game_id=game_visible.id,
        name="Hidden Inactive Category",
        slug="hidden-inactive-category",
        parent_id=None,
        status=ServiceCategoryStatus.INACTIVE,
        sort_order=3,
    )
    category_hidden_by_game = ServiceCategory(
        game_id=game_hidden.id,
        name="Hidden By Game Category",
        slug="hidden-by-game-category",
        parent_id=None,
        status=ServiceCategoryStatus.ACTIVE,
        sort_order=1,
    )
    db_session.add_all(
        [
            category_visible_primary,
            category_visible_secondary,
            category_hidden_inactive,
            category_hidden_by_game,
        ]
    )
    await db_session.flush()

    lot_visible_main = ServiceLot(
        category_id=category_visible_primary.id,
        name="Visible Main Lot",
        slug="visible-main-lot",
        description="Visible",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("20.00"),
    )
    lot_visible_badge = ServiceLot(
        category_id=category_visible_secondary.id,
        name="Visible Badge Lot",
        slug="visible-badge-lot",
        description="Visible badge",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("30.00"),
    )
    lot_hidden_unpublished = ServiceLot(
        category_id=category_visible_primary.id,
        name="Hidden Unpublished Lot",
        slug="hidden-unpublished-lot",
        description="Hidden unpublished",
        status=ServiceLotStatus.ACTIVE,
        base_price_eur=Decimal("25.00"),
    )
    db_session.add_all([lot_visible_main, lot_visible_badge, lot_hidden_unpublished])
    await db_session.flush()

    published_at = now_utc()
    db_session.add_all(
        [
            ServicePage(
                lot_id=lot_visible_main.id,
                status=ServicePageStatus.PUBLISHED,
                title="Visible Main Page",
                meta_json=None,
                published_at=published_at,
            ),
            ServicePage(
                lot_id=lot_visible_badge.id,
                status=ServicePageStatus.PUBLISHED,
                title="Visible Badge Page",
                meta_json=None,
                published_at=published_at,
            ),
            ServicePage(
                lot_id=lot_hidden_unpublished.id,
                status=ServicePageStatus.DRAFT,
                title="Hidden Draft Page",
                meta_json=None,
                published_at=None,
            ),
        ]
    )
    await db_session.flush()

    public_lot_discount = Promotion(
        audience=PromotionAudience.PUBLIC,
        lot_id=lot_visible_main.id,
        category_id=None,
        discount_type=PromotionDiscountType.PERCENT,
        discount_percent_value=20,
        discount_amount_eur=None,
        badge_tag=None,
        display_priority=1,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    public_lot_badge_hot = Promotion(
        audience=PromotionAudience.PUBLIC,
        lot_id=lot_visible_badge.id,
        category_id=None,
        discount_type=None,
        discount_percent_value=None,
        discount_amount_eur=None,
        badge_tag=PromotionBadgeTag.HOT,
        display_priority=1,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    public_category_badge_hot = Promotion(
        audience=PromotionAudience.PUBLIC,
        lot_id=None,
        category_id=category_visible_primary.id,
        discount_type=None,
        discount_percent_value=None,
        discount_amount_eur=None,
        badge_tag=PromotionBadgeTag.HOT,
        display_priority=2,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    # Legacy-invalid public category pricing row: should be excluded in public route.
    public_category_discount_invalid = Promotion(
        audience=PromotionAudience.PUBLIC,
        lot_id=None,
        category_id=category_visible_secondary.id,
        discount_type=PromotionDiscountType.PERCENT,
        discount_percent_value=35,
        discount_amount_eur=None,
        badge_tag=None,
        display_priority=3,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    personal_lot_discount = Promotion(
        audience=PromotionAudience.PERSONAL,
        lot_id=lot_visible_main.id,
        category_id=None,
        discount_type=PromotionDiscountType.FIXED_AMOUNT,
        discount_percent_value=None,
        discount_amount_eur=Decimal("5.00"),
        badge_tag=None,
        display_priority=4,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    personal_category_discount = Promotion(
        audience=PromotionAudience.PERSONAL,
        lot_id=None,
        category_id=category_visible_primary.id,
        discount_type=PromotionDiscountType.PERCENT,
        discount_percent_value=15,
        discount_amount_eur=None,
        badge_tag=None,
        display_priority=5,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    hidden_public_lot_badge = Promotion(
        audience=PromotionAudience.PUBLIC,
        lot_id=lot_hidden_unpublished.id,
        category_id=None,
        discount_type=None,
        discount_percent_value=None,
        discount_amount_eur=None,
        badge_tag=PromotionBadgeTag.HIT,
        display_priority=6,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    hidden_public_category_badge = Promotion(
        audience=PromotionAudience.PUBLIC,
        lot_id=None,
        category_id=category_hidden_inactive.id,
        discount_type=None,
        discount_percent_value=None,
        discount_amount_eur=None,
        badge_tag=PromotionBadgeTag.HIT,
        display_priority=7,
        is_enabled=True,
        starts_at=None,
        ends_at=None,
    )
    db_session.add_all(
        [
            public_lot_discount,
            public_lot_badge_hot,
            public_category_badge_hot,
            public_category_discount_invalid,
            personal_lot_discount,
            personal_category_discount,
            hidden_public_lot_badge,
            hidden_public_category_badge,
        ]
    )
    await db_session.flush()

    expires_at = now_utc() + timedelta(days=7)
    db_session.add_all(
        [
            PersonalPromotionAssignment(
                promotion_id=personal_lot_discount.id,
                user_id=customer_user.id,
                is_one_time=True,
                expires_at=expires_at,
            ),
            PersonalPromotionAssignment(
                promotion_id=personal_category_discount.id,
                user_id=customer_user.id,
                is_one_time=True,
                expires_at=expires_at,
            ),
        ]
    )
    await db_session.commit()

    return PublicPromotionsSeed(
        customer_user=customer_user,
        category_visible_primary=category_visible_primary,
        category_visible_secondary=category_visible_secondary,
        lot_visible_main=lot_visible_main,
        lot_visible_badge=lot_visible_badge,
        public_lot_discount_id=public_lot_discount.id,
        public_lot_badge_hot_id=public_lot_badge_hot.id,
        public_category_badge_hot_id=public_category_badge_hot.id,
        public_category_discount_invalid_id=public_category_discount_invalid.id,
        personal_lot_discount_id=personal_lot_discount.id,
        personal_category_discount_id=personal_category_discount.id,
        hidden_public_lot_badge_id=hidden_public_lot_badge.id,
        hidden_public_category_badge_id=hidden_public_category_badge.id,
    )


@pytest.mark.regression_catalog_promotions
async def test_public_promotions_lot_ids_lot_context_semantics(
    client: AsyncClient,
    public_promotions_seed: PublicPromotionsSeed,
) -> None:
    response = await client.get(
        "/api/v1/promotions",
        params={"lot_ids": [public_promotions_seed.lot_visible_main.id]},
    )
    assert response.status_code == 200
    items = _response_items(response.json())
    ids = _item_ids(items)

    assert public_promotions_seed.public_lot_discount_id in ids
    # By current BL, lot_ids pull category-level context via lot->category mapping.
    assert public_promotions_seed.public_category_badge_hot_id in ids
    assert public_promotions_seed.public_lot_badge_hot_id not in ids


@pytest.mark.regression_catalog_promotions
async def test_public_promotions_category_ids_filter(
    client: AsyncClient,
    public_promotions_seed: PublicPromotionsSeed,
) -> None:
    response = await client.get(
        "/api/v1/promotions",
        params={"category_ids": [public_promotions_seed.category_visible_primary.id]},
    )
    assert response.status_code == 200
    items = _response_items(response.json())
    ids = _item_ids(items)

    assert ids == {public_promotions_seed.public_category_badge_hot_id}


@pytest.mark.regression_catalog_promotions
async def test_public_promotions_badge_scope_all_lot_category(
    client: AsyncClient,
    public_promotions_seed: PublicPromotionsSeed,
) -> None:
    all_scope_response = await client.get(
        "/api/v1/promotions",
        params={"badge": "hot", "scope": "all"},
    )
    assert all_scope_response.status_code == 200
    all_scope_ids = _item_ids(_response_items(all_scope_response.json()))
    assert public_promotions_seed.public_lot_badge_hot_id in all_scope_ids
    assert public_promotions_seed.public_category_badge_hot_id in all_scope_ids

    lot_scope_response = await client.get(
        "/api/v1/promotions",
        params={"badge": "hot", "scope": "lot"},
    )
    assert lot_scope_response.status_code == 200
    lot_scope_ids = _item_ids(_response_items(lot_scope_response.json()))
    assert lot_scope_ids == {public_promotions_seed.public_lot_badge_hot_id}

    category_scope_response = await client.get(
        "/api/v1/promotions",
        params={"badge": "hot", "scope": "category"},
    )
    assert category_scope_response.status_code == 200
    category_scope_ids = _item_ids(_response_items(category_scope_response.json()))
    assert category_scope_ids == {public_promotions_seed.public_category_badge_hot_id}


@pytest.mark.regression_catalog_promotions
async def test_public_promotions_unauthorized_vs_authorized_personal(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    public_promotions_seed: PublicPromotionsSeed,
) -> None:
    query_params = {"lot_ids": [public_promotions_seed.lot_visible_main.id]}

    unauthorized_response = await client.get(
        "/api/v1/promotions",
        params=query_params,
    )
    assert unauthorized_response.status_code == 200
    unauthorized_items = _response_items(unauthorized_response.json())
    assert {item["source"] for item in unauthorized_items} == {"PUBLIC"}
    unauthorized_ids = _item_ids(unauthorized_items)
    assert public_promotions_seed.personal_lot_discount_id not in unauthorized_ids
    assert (
        public_promotions_seed.personal_category_discount_id
        not in unauthorized_ids
    )

    authorized_response = await client.get(
        "/api/v1/promotions",
        params=query_params,
        headers=auth_headers(
            role=UserRole.CUSTOMER,
            user_id=public_promotions_seed.customer_user.id,
        ),
    )
    assert authorized_response.status_code == 200
    authorized_items = _response_items(authorized_response.json())
    authorized_ids = _item_ids(authorized_items)
    assert public_promotions_seed.personal_lot_discount_id in authorized_ids
    assert public_promotions_seed.personal_category_discount_id in authorized_ids
    assert {item["source"] for item in authorized_items} == {
        "PUBLIC",
        "PERSONAL",
    }


@pytest.mark.regression_catalog_promotions
async def test_public_promotions_hidden_scope_excluded(
    client: AsyncClient,
    public_promotions_seed: PublicPromotionsSeed,
) -> None:
    response = await client.get(
        "/api/v1/promotions",
        params={"badge": "hit"},
    )
    assert response.status_code == 200
    items = _response_items(response.json())
    ids = _item_ids(items)

    assert public_promotions_seed.hidden_public_lot_badge_id not in ids
    assert public_promotions_seed.hidden_public_category_badge_id not in ids
    assert ids == set()


@pytest.mark.regression_catalog_promotions
async def test_public_category_visual_only_and_personal_category_pricing(
    client: AsyncClient,
    auth_headers: Callable[..., dict[str, str]],
    public_promotions_seed: PublicPromotionsSeed,
) -> None:
    unauthorized_secondary_category_response = await client.get(
        "/api/v1/promotions",
        params={"category_ids": [public_promotions_seed.category_visible_secondary.id]},
    )
    assert unauthorized_secondary_category_response.status_code == 200
    unauthorized_items = _response_items(
        unauthorized_secondary_category_response.json()
    )
    # Legacy-invalid PUBLIC category discount row is filtered out in public route.
    assert _item_ids(unauthorized_items) == set()
    assert (
        public_promotions_seed.public_category_discount_invalid_id
        not in _item_ids(unauthorized_items)
    )

    authorized_primary_category_response = await client.get(
        "/api/v1/promotions",
        params={"category_ids": [public_promotions_seed.category_visible_primary.id]},
        headers=auth_headers(
            role=UserRole.CUSTOMER,
            user_id=public_promotions_seed.customer_user.id,
        ),
    )
    assert authorized_primary_category_response.status_code == 200
    authorized_items = _response_items(authorized_primary_category_response.json())
    authorized_ids = _item_ids(authorized_items)

    assert public_promotions_seed.public_category_badge_hot_id in authorized_ids
    # PERSONAL category discount is allowed and visible for authorized user.
    assert public_promotions_seed.personal_category_discount_id in authorized_ids
    personal_category_item = next(
        item
        for item in authorized_items
        if item["promotion_id"] == public_promotions_seed.personal_category_discount_id
    )
    assert personal_category_item["source"] == "PERSONAL"
    assert personal_category_item["discount_type"] == "percent"
    assert personal_category_item["discount_percent_value"] == 15
