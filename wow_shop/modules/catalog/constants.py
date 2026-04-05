"""Catalog module constants."""

from __future__ import annotations

import re

CATEGORY_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
GAME_SLUG_PATTERN = CATEGORY_SLUG_PATTERN
LOT_SLUG_PATTERN = CATEGORY_SLUG_PATTERN
LOT_OPTION_CODE_PATTERN = CATEGORY_SLUG_PATTERN
LOT_OPTION_VALUE_CODE_PATTERN = CATEGORY_SLUG_PATTERN
CATEGORY_SCOPE_SLUG_CONSTRAINTS = frozenset(
    {
        "uq_catalog_service_categories__game_id_parent_id_slug",
        "uq_catalog_service_categories__game_id_slug__root",
    }
)
GAME_SLUG_CONSTRAINTS = frozenset(
    {
        "uq_catalog_games__slug",
        "catalog_games_slug_key",
    }
)
LOT_SCOPE_SLUG_CONSTRAINTS = frozenset(
    {
        "uq_catalog_service_lots__category_id_slug",
        "catalog_service_lots_category_id_slug_key",
    }
)
LOT_OPTION_SCOPE_CODE_CONSTRAINTS = frozenset(
    {
        "uq_catalog_lot_options__lot_id_code",
        "catalog_lot_options_lot_id_code_key",
    }
)
LOT_OPTION_VALUE_SCOPE_CODE_CONSTRAINTS = frozenset(
    {
        "uq_catalog_lot_option_values__option_id_code",
        "catalog_lot_option_values_option_id_code_key",
    }
)
