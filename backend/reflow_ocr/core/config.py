"""Application settings and configuration helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from platformdirs import user_data_dir
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    """Return platform-specific directory for persistent artifacts."""
    return Path(user_data_dir(appname="ReflowOCR", appauthor="Reflow")).resolve()


class Settings(BaseSettings):
    """Global application settings."""

    app_name: str = "Reflow OCR Backend"
    env: Literal["development", "production", "test"] = "development"
    api_prefix: str = "/api"
    data_dir: Path = Field(default_factory=_default_data_dir)
    log_level: str = "INFO"
    autosave_interval_seconds: int = 30

    model_config = SettingsConfigDict(
        env_prefix="REFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings


def reload_settings() -> Settings:
    """Reset cache and create a new settings instance (used in tests)."""
    get_settings.cache_clear()
    return get_settings()


# Convenience alias used across the codebase.
settings = get_settings()
