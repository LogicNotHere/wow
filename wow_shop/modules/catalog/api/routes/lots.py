from fastapi import APIRouter

public_router = APIRouter(prefix="/lots", tags=["catalog"])
staff_router = APIRouter(prefix="/lots", tags=["catalog"])

__all__ = [
    "public_router",
    "staff_router",
]
