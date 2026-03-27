from wow_shop.core.errors import ApplicationError


class TokenError(ApplicationError):
    """Base token error."""


class TokenMissingError(TokenError):
    """Token is missing in request context."""


class TokenInvalidError(TokenError):
    """Token has invalid signature or payload."""


class TokenInvalidRoleError(TokenInvalidError):
    """Token contains unsupported role value."""


class TokenExpiredError(TokenError):
    """Token is expired."""


class RefreshTokenRevokedError(TokenError):
    """Refresh token jti is missing in Redis."""


class RefreshTokenConflictError(TokenError):
    """Refresh token jti already exists in Redis."""
