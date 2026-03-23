import uvicorn

from wow_shop.core.config_loader import init_config, get_settings


def main() -> None:
    init_config()
    settings = get_settings()

    uvicorn.run(
        "wow_shop.app:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
    )


if __name__ == "__main__":
    main()
