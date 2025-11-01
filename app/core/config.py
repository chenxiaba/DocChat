"""Application configuration management."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

try:  # Pydantic v2
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except ImportError:  # Fallback to Pydantic v1
    from pydantic import BaseSettings  # type: ignore
    SettingsConfigDict = None  # type: ignore

from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    openai_api_base: str = Field(
        default="https://api.deepseek.com/v1", alias="OPENAI_API_BASE"
    )
    db_path: str = Field(default="data/memory.sqlite", alias="DB_PATH")
    vector_db_path: str = Field(default="data/vector_store", alias="VECTOR_DB_PATH")
    chat_history_path: str = Field(
        default="data/chat_history.pkl", alias="CHAT_HISTORY_PATH"
    )

    if SettingsConfigDict:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")  # type: ignore[assignment]
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            allow_mutation = False


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""

    return Settings()


__all__ = ["Settings", "get_settings"]
