"""Application configuration management using Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Centralised application settings."""

    model_config = SettingsConfigDict(
        env_file=(".env",), env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: str = Field(default="development", alias="DOCCHAT_ENV")
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    openai_api_base: str = Field(default="https://api.deepseek.com/v1", alias="OPENAI_API_BASE")

    data_dir: Path = Field(default=Path("data"), alias="DOCCHAT_DATA_DIR")
    database_url: Optional[str] = Field(default=None, alias="DOCCHAT_DATABASE_URL")

    allowed_origins: List[str] = Field(default_factory=list, alias="DOCCHAT_ALLOWED_ORIGINS")
    api_keys: List[str] = Field(default_factory=list, alias="DOCCHAT_API_KEYS")

    max_upload_size_mb: int = Field(default=16, alias="DOCCHAT_MAX_UPLOAD_MB")

    log_json: bool = Field(default=True, alias="DOCCHAT_LOG_JSON")

    google_client_id: Optional[str] = Field(default=None, alias="DOCCHAT_GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, alias="DOCCHAT_GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = Field(default=None, alias="DOCCHAT_GOOGLE_REDIRECT_URI")

    wechat_app_id: Optional[str] = Field(default=None, alias="DOCCHAT_WECHAT_APP_ID")
    wechat_app_secret: Optional[str] = Field(default=None, alias="DOCCHAT_WECHAT_APP_SECRET")
    wechat_redirect_uri: Optional[str] = Field(default=None, alias="DOCCHAT_WECHAT_REDIRECT_URI")

    oauth_state_ttl_seconds: int = Field(default=600, alias="DOCCHAT_OAUTH_STATE_TTL", ge=60)
    oauth_http_timeout_seconds: float = Field(default=10.0, alias="DOCCHAT_OAUTH_HTTP_TIMEOUT", gt=0)

    @field_validator("allowed_origins", "api_keys", mode="before")
    @classmethod
    def _parse_csv(cls, value: Iterable[str] | str | None) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return _split_csv(value)
        return [item for item in value if item]

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "memory.sqlite"

    @property
    def vector_db_path(self) -> Path:
        return self.data_dir / "vector_store"

    @property
    def chat_history_path(self) -> Path:
        return self.data_dir / "chat_history.pkl"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        sqlite_path = self.sqlite_path
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_path.as_posix()}"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings

