import os
from dataclasses import dataclass


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    app_debug: bool = _read_bool("APP_DEBUG", True)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    postgres_db: str = os.getenv("POSTGRES_DB", "wow_shop")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/wow_shop",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    cors_allow_origins: str = os.getenv(
        "CORS_ALLOW_ORIGINS", "http://localhost:3000"
    )
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")


settings = Settings()
