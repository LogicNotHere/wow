from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class YamlStrEnum(str, Enum):
    pass


class LogLevel(YamlStrEnum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    env: str
    debug: bool
    host: str
    port: int
    log_level: LogLevel


class DbSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


class RedisSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


class JwtSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret_key: str
    algorithm: str
    issuer: str
    access_ttl_minutes: int
    refresh_ttl_days: int


class CorsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_origins: list[str]


class SentrySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dsn: str


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppSettings
    db: DbSettings
    redis: RedisSettings
    jwt: JwtSettings
    cors: CorsSettings
    sentry: SentrySettings
