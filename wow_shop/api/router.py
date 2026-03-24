from __future__ import annotations

from fastapi import Depends, APIRouter

from wow_shop.api.responses import COMMON_RESPONSES
from wow_shop.api.dependencies.auth import get_current_user
from wow_shop.modules.auth.api.routes import (
    public_router as auth_public_feature_router,
)
from wow_shop.infrastructure.db.session import handle_session
from wow_shop.api.dependencies.permissions import (
    require_admin_access,
    require_booster_access,
)

auth_public_router = APIRouter(
    responses=COMMON_RESPONSES,
    dependencies=[Depends(handle_session)],
)
booster_router = APIRouter(
    responses=COMMON_RESPONSES,
    dependencies=[
        Depends(handle_session),
        Depends(get_current_user),
        Depends(require_booster_access),
    ],
)
admin_router = APIRouter(
    responses=COMMON_RESPONSES,
    dependencies=[
        Depends(handle_session),
        Depends(get_current_user),
        Depends(require_admin_access),
    ],
)

auth_public_router.include_router(auth_public_feature_router)
