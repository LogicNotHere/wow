from __future__ import annotations

from sqlalchemy import select

from wow_shop.infrastructure.db.session import s
from wow_shop.modules.auth.constants import PASSWORD_MIN_LENGTH
from wow_shop.modules.auth.application.errors import (
    AuthValidationError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
)
from wow_shop.modules.auth.application.passwords import (
    hash_password,
    verify_password,
)
from wow_shop.infrastructure.security.token_service import (
    TokenPair,
    TokenService,
)
from wow_shop.modules.auth.infrastructure.db.models import User, UserRole


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_email(email: str) -> str:
    normalized_email = _normalize_email(email)
    if "@" not in normalized_email or "." not in normalized_email:
        raise AuthValidationError("Invalid email format.")
    return normalized_email


def _validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AuthValidationError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )


def _resolve_role_for_access_token(user: User) -> str:
    return user.role.value


async def _get_user_by_email(email: str) -> User | None:
    query = select(User).where(User.email == email)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def _get_user_by_id(user_id: int) -> User | None:
    query = select(User).where(User.id == user_id)
    result = await s.db.execute(query)
    return result.scalar_one_or_none()


async def register_user(
    email: str,
    password: str,
    token_service: TokenService,
) -> TokenPair:
    validated_email = _validate_email(email)
    _validate_password(password)

    existing_user = await _get_user_by_email(validated_email)
    if existing_user is not None:
        raise UserAlreadyExistsError("User already exists.")

    user = User(
        email=validated_email,
        password_hash=hash_password(password),
        role=UserRole.CUSTOMER,
    )
    s.db.add(user)
    await s.db.flush()
    await s.db.refresh(user)

    return await token_service.issue_token_pair(
        user_id=user.id,
        role=_resolve_role_for_access_token(user),
    )


async def login_user(
    email: str,
    password: str,
    token_service: TokenService,
) -> TokenPair:
    validated_email = _validate_email(email)
    user = await _get_user_by_email(validated_email)

    if user is None or user.password_hash is None:
        raise InvalidCredentialsError("Invalid credentials.")
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid credentials.")

    return await token_service.issue_token_pair(
        user_id=user.id,
        role=_resolve_role_for_access_token(user),
    )


async def refresh_tokens(
    refresh_token: str,
    token_service: TokenService,
) -> TokenPair:
    payload = token_service.parse_refresh_token(refresh_token)
    user = await _get_user_by_id(payload.user_id)
    if user is None:
        raise InvalidCredentialsError("User not found.")

    return await token_service.refresh_tokens(
        refresh_payload=payload,
        role=_resolve_role_for_access_token(user),
    )


async def logout(refresh_token: str, token_service: TokenService) -> None:
    await token_service.logout_refresh_token(refresh_token=refresh_token)
