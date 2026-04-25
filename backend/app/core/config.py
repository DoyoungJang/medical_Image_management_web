from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PNG 탐색기"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api"

    png_root_dir: str = "./data/png"
    thumbnail_cache_dir: str = "./data/thumb-cache"
    database_url: str = "sqlite:///./png_browser.db"

    auto_scan_on_startup: bool = False
    periodic_scan_interval_seconds: int = 300
    allow_symlinks: bool = False
    public_show_absolute_path: bool = False
    enable_watchdog: bool = False
    use_fts5: bool = True

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    auth_enabled: bool = True
    auth_username: str = "admin"
    auth_password: str = ""
    auth_password_hash: str = ""
    auth_cookie_name: str = "png_browser_session"
    auth_secret_key: str = "change-me-in-production"
    auth_session_ttl_hours: int = 12

    default_page_size: int = 24
    max_page_size: int = 100
    thumbnail_default_size: int = 256
    thumbnail_max_size: int = 512

    admin_rescan_cooldown_seconds: int = 10
    max_metadata_text_length: int = 200_000
    max_png_text_bytes: int = 512_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return []
            if raw_value.startswith("["):
                parsed = json.loads(raw_value)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON value must be a list")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in raw_value.split(",") if item.strip()]
        raise ValueError("CORS_ORIGINS must be a comma-separated string or list")


@lru_cache
def get_settings() -> Settings:
    return Settings()
