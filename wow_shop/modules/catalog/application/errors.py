from __future__ import annotations

from wow_shop.core.errors import ApplicationError


class CatalogError(ApplicationError):
    """Base catalog flow error."""


class CatalogValidationError(CatalogError):
    """Catalog request payload is invalid."""


class ParentCategoryNotFoundError(CatalogError):
    """Parent category does not exist."""


class CategoryAlreadyExistsError(CatalogError):
    """Category slug already exists in the same parent scope."""


class GameNotFoundError(CatalogError):
    """Game does not exist."""


class GameAlreadyExistsError(CatalogError):
    """Game slug already exists."""


class CategoryNotFoundError(CatalogError):
    """Category does not exist."""


class LotNotFoundError(CatalogError):
    """Lot does not exist."""


class LotAlreadyExistsError(CatalogError):
    """Lot slug already exists in category scope."""


class LotPageNotFoundError(CatalogError):
    """Lot page does not exist."""


class LotPageBlockNotFoundError(CatalogError):
    """Lot page block does not exist."""


class LotOptionNotFoundError(CatalogError):
    """Lot option does not exist."""


class LotOptionAlreadyExistsError(CatalogError):
    """Lot option code already exists in lot scope."""


class LotOptionValueNotFoundError(CatalogError):
    """Lot option value does not exist."""


class LotOptionValueAlreadyExistsError(CatalogError):
    """Lot option value code already exists in option scope."""
