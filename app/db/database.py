"""Database utilities and session management."""
from __future__ import annotations

import contextlib
import logging
import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "sqlite:///./app.db"


def get_database_url() -> str:
    """Return the configured database URL.

    Prefers the ``DATABASE_URL`` environment variable and falls back to a local
    SQLite database for development convenience. The function also normalises
    ``postgres://`` URLs, which are sometimes emitted by cloud providers, to the
    ``postgresql://`` format understood by SQLAlchemy.
    """

    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def create_engine_and_sessionmaker() -> tuple[sessionmaker[Session], Engine]:
    """Create the SQLAlchemy engine and session factory."""

    database_url = get_database_url()
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, echo=False, future=True, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return session_factory, engine


SessionLocalFactory, engine = create_engine_and_sessionmaker()


@contextlib.contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session: Session = SessionLocalFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Rolling back session due to error")
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a session."""

    with session_scope() as session:
        yield session
