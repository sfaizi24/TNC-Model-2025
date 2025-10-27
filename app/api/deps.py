"""FastAPI dependency utilities."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.database import get_session
from app.settings import Settings, get_settings


def get_db_session() -> Session:
    yield from get_session()


def get_app_settings() -> Settings:
    return get_settings()
