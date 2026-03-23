from __future__ import annotations

from fastapi import APIRouter, Depends

from wow_shop.api.dependencies.auth import get_current_user
from wow_shop.api.dependencies.permissions import (
    require_admin_access,
    require_booster_access,
)
from wow_shop.api.responses import COMMON_RESPONSES
from wow_shop.infrastructure.db.session import get_db_session
from wow_shop.modules.auth.api.routes import (
    customer_router as auth_customer_feature_router,
    public_router as auth_public_feature_router,
)

auth_public_router = APIRouter(
    responses=COMMON_RESPONSES,
    dependencies=[Depends(get_db_session)],
)
customer_router = APIRouter(
    responses=COMMON_RESPONSES,
    dependencies=[
        Depends(get_db_session),
        Depends(get_current_user),
    ],
)
booster_router = APIRouter(
    responses=COMMON_RESPONSES,
    dependencies=[
        Depends(get_db_session),
        Depends(get_current_user),
        Depends(require_booster_access),
    ],
)
admin_router = APIRouter(
    responses=COMMON_RESPONSES,
    dependencies=[
        Depends(get_db_session),
        Depends(get_current_user),
        Depends(require_admin_access),
    ],
)

auth_public_router.include_router(auth_public_feature_router)
customer_router.include_router(auth_customer_feature_router)
