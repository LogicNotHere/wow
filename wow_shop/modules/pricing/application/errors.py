from __future__ import annotations

from wow_shop.core.errors import ApplicationError


class PricingError(ApplicationError):
    """Base pricing flow error."""


class PromotionValidationError(PricingError):
    """Promotion payload is invalid."""


class PromotionLotNotFoundError(PricingError):
    """Promotion lot scope does not exist."""


class PromotionCategoryNotFoundError(PricingError):
    """Promotion category scope does not exist."""


class PromotionTargetUserNotFoundError(PricingError):
    """Promotion target user does not exist."""


class PromotionNotFoundError(PricingError):
    """Promotion does not exist."""


class PromotionAssignmentAlreadyExistsError(PricingError):
    """Promotion assignment already exists for user."""


class PromotionAssignmentNotFoundError(PricingError):
    """Promotion assignment does not exist."""
