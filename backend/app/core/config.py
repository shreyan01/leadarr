"""Centralized application configuration.

All runtime configuration is sourced from environment variables (see
``.env.example``). Nothing in the rest of the codebase should read
``os.environ`` directly — inject ``Settings`` via ``get_settings`` instead so
behaviour stays testable and overridable.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Checks both locations so this works whether the process is
        # launched from the repo root (Docker Compose's env_file: .env)
        # or from backend/ directly (e.g. `cd backend && alembic ...`,
        # which is a common bare-metal workflow). Both are loaded if
        # present; a later entry overrides an earlier one on conflict.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "LeadForge"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    # Stored as plain CSV text (not list[str]) so pydantic-settings never
    # attempts to JSON-decode it — that auto-decoding of "complex" field
    # types happens before any custom parsing logic runs, and unquoted CSV
    # from a .env file (http://a,http://b) isn't valid JSON. Splitting into
    # a list happens explicitly in the property below instead.
    BACKEND_CORS_ORIGINS_CSV: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")

    # --- Database ---
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://leadforge:leadforge@postgres:5432/leadforge"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql+psycopg2://leadforge:leadforge@postgres:5432/leadforge",
        description="Sync URL used by Alembic migrations.",
    )

    # --- Redis / Celery ---
    REDIS_URL: RedisDsn = Field(default="redis://redis:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/2")

    # --- Auth ---
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # --- AI Providers ---
    AI_CHAT_PROVIDER: Literal[
        "openai", "anthropic", "gemini", "ollama", "openrouter", "qwen"
    ] = "qwen"
    AI_VISION_PROVIDER: Literal[
        "openai", "anthropic", "gemini", "qwen_vl", "ollama"
    ] = "qwen_vl"
    AI_EMBEDDING_PROVIDER: Literal["openai", "gemini", "ollama", "qwen"] = "qwen"

    ANTHROPIC_API_KEY: SecretStr | None = None
    OPENAI_API_KEY: SecretStr | None = None
    GEMINI_API_KEY: SecretStr | None = None
    OPENROUTER_API_KEY: SecretStr | None = None
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    QWEN_VL_BASE_URL: str = "http://qwen-vl:8001"
    QWEN_EMBED_BASE_URL: str = "http://qwen-embed:8002"

    DEFAULT_CHAT_MODEL: str = "qwen2.5-vl-7b"
    DEFAULT_VISION_MODEL: str = "qwen2.5-vl-7b"
    DEFAULT_EMBEDDING_MODEL: str = "qwen3-embedding-0.6b"

    # --- Email ---
    EMAIL_PROVIDER: Literal["smtp", "resend", "sendgrid", "ses"] = "smtp"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: SecretStr | None = None
    RESEND_API_KEY: SecretStr | None = None
    SENDGRID_API_KEY: SecretStr | None = None
    AWS_SES_REGION: str | None = None
    EMAIL_FROM_ADDRESS: str = "noreply@leadforge.local"

    # --- Discovery ---
    DISCOVERY_PROVIDER: Literal["google_places", "osm"] = "osm"
    GOOGLE_PLACES_API_KEY: SecretStr | None = None

    # --- Storage ---
    STORAGE_BACKEND: Literal["local", "minio"] = "local"
    LOCAL_STORAGE_PATH: str = "./storage"
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: SecretStr | None = None
    MINIO_BUCKET: str = "leadforge"

    # --- Lighthouse / Playwright ---
    LIGHTHOUSE_CLI_PATH: str = "lighthouse"
    PLAYWRIGHT_HEADLESS: bool = True

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS_CSV.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — use as a FastAPI dependency."""
    return Settings()