"""
Assistance Service Configuration

Reads all settings from environment variables with sane defaults.
No secrets are hard-coded — all keys come from .env or container environment.
"""

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class AssistanceSettings(BaseSettings):
    """
    Configuration for the Advanced Assistance microservice.

    All fields can be overridden via environment variables.
    Prefix: ASSISTANCE_ (e.g. ASSISTANCE_PORT=8001)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASSISTANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Service ──────────────────────────────────────────────────────────
    port: int = 8001
    debug: bool = False
    log_level: str = "info"

    # ── Cross-service ────────────────────────────────────────────────────
    main_backend_url: str = "http://localhost:8000"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Qdrant ───────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # ── LLM ──────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache(maxsize=1)
def get_settings() -> AssistanceSettings:
    """Return a cached settings instance (singleton)."""
    return AssistanceSettings()

# Made with Bob
