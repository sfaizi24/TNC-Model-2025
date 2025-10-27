"""Application settings loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sleeper_league_id: str = Field(
        "1226433368405585920", alias="SLEEPER_LEAGUE_ID", description="Sleeper league identifier"
    )
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    cache_dir: str = Field(default="cache", alias="CACHE_DIR")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
