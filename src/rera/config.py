"""Application configuration loaded from environment variables / .env.

Values are intentionally centralised here so nothing is hard-coded deep inside
the ingestion code. See ``.env.example`` for the full set of supported keys.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Environment variable names are matched case-insensitively, so the field
    ``database_url`` is populated by ``DATABASE_URL``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/rera.db",
        description="SQLAlchemy database URL.",
    )
    read_only_database_url: str | None = Field(
        default=None,
        description="Optional read-only URL used by the analytics API (falls back to DATABASE_URL).",
    )

    # Source
    rera_base_url: str = Field(default="https://rera.kerala.gov.in")
    rera_request_delay_seconds: float = Field(default=2.0, ge=0)
    rera_max_retries: int = Field(default=3, ge=0)
    rera_timeout_seconds: int = Field(default=30, gt=0)
    rera_user_agent: str = Field(
        default="KeralaRERA-Intelligence/0.1 (+research; contact via repository)"
    )

    # Storage
    raw_data_path: Path = Field(default=Path("./data/raw"))
    manual_import_path: Path = Field(default=Path("./data/raw/manual"))
    sample_data_path: Path = Field(default=Path("./data/sample"))
    processed_data_path: Path = Field(default=Path("./data/processed"))

    # Logging
    log_level: str = Field(default="INFO")

    # Parser
    parser_version: str = Field(default="1.0.0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""

    return Settings()
