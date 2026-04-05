from fastapi import APIRouter

from wow_shop.modules.catalog.api.routes.categories import (
    public_router as categories_public_router,
    staff_router as categories_staff_router,
)
from wow_shop.modules.catalog.api.routes.games import (
    public_router as games_public_router,
    staff_router as games_staff_router,
)
from wow_shop.modules.catalog.api.routes.lots import (
    public_router as lots_public_router,
    staff_router as lots_staff_router,
)

public_router = APIRouter()
public_router.include_router(games_public_router)
public_router.include_router(categories_public_router)
public_router.include_router(lots_public_router)

staff_router = APIRouter()
staff_router.include_router(games_staff_router)
staff_router.include_router(categories_staff_router)
staff_router.include_router(lots_staff_router)
