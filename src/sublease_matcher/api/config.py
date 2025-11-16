from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "sublease-matcher-api"
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    database_url: str | None = None
    storage: str = "memory"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SM_")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        raise ValueError("cors_origins must be a list or comma-separated string")

    @field_validator("storage", mode="before")
    @classmethod
    def _normalize_storage(cls, value: Any) -> str:
        if value is None:
            return "memory"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"memory", "sqlalchemy"}:
                return normalized
        raise ValueError("storage must be either 'memory' or 'sqlalchemy'")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
