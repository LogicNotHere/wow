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
