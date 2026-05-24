from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "AI Algorithmic Trading Platform"
    environment: str = "development"
    database_url: str = "sqlite:///./trading_platform.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    mt5_login: Optional[int] = None
    mt5_server: Optional[str] = None
    mt5_password: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for reuse across the backend."""

    return Settings()
