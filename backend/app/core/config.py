"""Application configuration management."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AIEO API"
    APP_VERSION: str = "0.3.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = "postgresql://aieo:aieo@localhost:5432/aieo"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 86400  # 24 hours in seconds

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_AI_MODEL: str = "gpt-5.4"
    WORKSPACE_ROOT: str = ".aieo-workspace"

    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    RATE_LIMIT_PER_MINUTE: int = 60

    # External integrations (optional)
    GA4_PROPERTY_ID: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GSC_SITE_URL: Optional[str] = None
    DATAFORSEO_LOGIN: Optional[str] = None
    DATAFORSEO_PASSWORD: Optional[str] = None
    DATAFORSEO_BASE_URL: str = "https://api.dataforseo.com"

    # Publishing
    WP_URL: Optional[str] = None
    WP_USERNAME: Optional[str] = None
    WP_APP_PASSWORD: Optional[str] = None

    # Content Limits
    MAX_CONTENT_WORDS: int = 50000
    MAX_CONTENT_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB

    # Citation Tracking
    CITATION_PROBE_INTERVAL_HOURS: int = 24
    CITATION_DETECTION_ENGINES: list[str] = ["grok", "claude"]

    # Skip .env when AIEO_HEADLESS=1 (CI / headless runner: env vars only)
    model_config = SettingsConfigDict(
        env_file=(".env" if os.environ.get("AIEO_HEADLESS") != "1" else None),
        case_sensitive=True,
    )


settings = Settings()


def workspace_root() -> Path:
    """Resolve workspace path from configured root."""
    return Path(settings.WORKSPACE_ROOT).resolve()
