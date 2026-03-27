"""Catalog module constants."""

from __future__ import annotations

import re

CATEGORY_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
GAME_SLUG_PATTERN = CATEGORY_SLUG_PATTERN
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
