from fastapi import FastAPI

from wow_shop.core.config import settings


app = FastAPI(title="WowShop API", debug=settings.app_debug)


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.app_env,
    }
