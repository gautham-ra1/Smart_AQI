"""Application configuration loaded strictly from environment variables (.env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ENV_FILE = str(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "VayuMesh Hyperlocal AQI"
    DEFAULT_CITY: str = "chikkamagaluru"

    DATABASE_URL: str = "postgresql+asyncpg://gauthamrajykotian@localhost:5432/vayumesh_aqi"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "vayumesh-chikkamagaluru-dev-jwt-secret-key-2026-avishkar"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 180
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    API_KEY_PEPPER: str = "vayumesh-hmac-sha256-pepper-secret-2026"

    INGEST_RATE_LIMIT_PER_MIN: int = 12
    INGEST_RATE_MIN_PER_MIN: int = 1
    INGEST_GLOBAL_BUDGET_PER_MIN: int = 180
    INGEST_RATE_WINDOW_SEC: int = 60

    DATA_GOV_API_KEY: str = ""
    OPENAQ_API_KEY: str = ""

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
