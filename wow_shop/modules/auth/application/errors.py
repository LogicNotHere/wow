from __future__ import annotations

from wow_shop.core.errors import ApplicationError


class AuthError(ApplicationError):
    """Base auth flow error."""


class UserAlreadyExistsError(AuthError):
    """User with this email already exists."""


class InvalidCredentialsError(AuthError):
    """Invalid login or password."""


class AuthValidationError(AuthError):
    """Invalid auth input."""
