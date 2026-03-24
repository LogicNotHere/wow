from __future__ import annotations

from fastapi import Depends, APIRouter
from starlette import status

from wow_shop.api.responses import ErrorResponseModel
from wow_shop.shared.contracts import BaseHttpResponseModel
from wow_shop.modules.auth.api.request.models import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
)
from wow_shop.modules.auth.api.response.models import TokenPairResponse
from wow_shop.infrastructure.security.token_service import (
    TokenService,
    get_token_service,
)
from wow_shop.modules.auth.application.auth_service import (
    logout,
    login_user,
    register_user,
    refresh_tokens,
)

public_router = APIRouter(tags=["auth"])


@public_router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    description="Register user and issue access/refresh tokens.",
    response_model=BaseHttpResponseModel[TokenPairResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[TokenPairResponse],
            "description": "Registered user token pair.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid email/password input.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "User with this email already exists.",
        },
    },
)
async def register(
    payload: RegisterRequest,
    token_service: TokenService = Depends(get_token_service),
) -> BaseHttpResponseModel[TokenPairResponse]:
    token_pair = await register_user(
        email=payload.email,
        password=payload.password,
        token_service=token_service,
    )

    return BaseHttpResponseModel(
        data=TokenPairResponse.build(token_pair),
        message="Register success",
    )


@public_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    description="Login user and issue access/refresh tokens.",
    response_model=BaseHttpResponseModel[TokenPairResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[TokenPairResponse],
            "description": "Authenticated user token pair.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseModel,
            "description": "Invalid login input format.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponseModel,
            "description": "Invalid credentials.",
        },
    },
)
async def login(
    payload: LoginRequest,
    token_service: TokenService = Depends(get_token_service),
) -> BaseHttpResponseModel[TokenPairResponse]:
    token_pair = await login_user(
        email=payload.email,
        password=payload.password,
        token_service=token_service,
    )

    return BaseHttpResponseModel(
        data=TokenPairResponse.build(token_pair),
        message="Login success",
    )


@public_router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    description="Refresh token pair using refresh token.",
    response_model=BaseHttpResponseModel[TokenPairResponse],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[TokenPairResponse],
            "description": "Refreshed user token pair.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponseModel,
            "description": (
                "Refresh token invalid, expired, revoked, or user not found."
            ),
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponseModel,
            "description": "Refresh token rotation conflict.",
        },
    },
)
async def refresh(
    payload: RefreshRequest,
    token_service: TokenService = Depends(get_token_service),
) -> BaseHttpResponseModel[TokenPairResponse]:
    token_pair = await refresh_tokens(
        refresh_token=payload.refresh_token,
        token_service=token_service,
    )

    return BaseHttpResponseModel(
        data=TokenPairResponse.build(token_pair),
        message="Refresh success",
    )


@public_router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    description="Logout user by revoking refresh token.",
    response_model=BaseHttpResponseModel[None],
    responses={
        status.HTTP_200_OK: {
            "model": BaseHttpResponseModel[None],
            "description": "Logout operation status.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponseModel,
            "description": "Refresh token invalid or expired.",
        },
    },
)
async def logout_route(
    payload: LogoutRequest,
    token_service: TokenService = Depends(get_token_service),
) -> BaseHttpResponseModel[None]:
    await logout(
        refresh_token=payload.refresh_token,
        token_service=token_service,
    )

    return BaseHttpResponseModel(message="Logged out.")
