from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from wow_shop.core.config import Settings


CONFIG_ENV = "CONFIG"
OVERRIDE_CONFIG_ENV = "OVERRIDE_CONFIG"


class ConfigError(Exception):
    pass


def _resolve_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else Path.cwd() / path


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file does not exist: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}

    if not isinstance(payload, dict):
        raise ConfigError(f"Config file must contain a YAML object: {path}")
    return payload


def _deep_merge(
    base: Mapping[str, Any], override: Mapping[str, Any]
) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current_value = merged.get(key)
        if isinstance(current_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current_value, value)
            continue
        merged[key] = value
    return merged


def load_settings(
    config_path: str | Path | None = None,
    override_config_path: str | Path | None = None,
) -> Settings:
    raw_base_path = config_path or os.getenv(CONFIG_ENV)
    if not raw_base_path:
        raise ConfigError(
            "Config should be specified with env var CONFIG."
        )

    base_path = _resolve_path(raw_base_path)
    base_payload = _read_yaml(base_path)

    raw_override_path = (
        override_config_path
        if override_config_path is not None
        else os.getenv(OVERRIDE_CONFIG_ENV)
    )

    merged_payload = base_payload
    if raw_override_path:
        override_path = _resolve_path(raw_override_path)
        override_payload = _read_yaml(override_path)
        merged_payload = _deep_merge(base_payload, override_payload)

    return Settings.model_validate(merged_payload)


class Config:
    c: Settings | None = None


def init_config(
    config_path: str | Path | None = None,
    override_config_path: str | Path | None = None,
) -> None:
    Config.c = load_settings(
        config_path=config_path,
        override_config_path=override_config_path,
    )


def get_settings() -> Settings:
    if Config.c is None:
        raise ConfigError(
            "Config is not initialized. Call init_config() first."
        )
    return Config.c
