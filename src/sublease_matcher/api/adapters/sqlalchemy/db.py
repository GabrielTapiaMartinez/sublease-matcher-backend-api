from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_lock = Lock()


def configure_engine(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    """Initialize (or reuse) the shared SQLAlchemy engine and session factory."""
    if not database_url:
        raise RuntimeError("SM_DATABASE_URL is required when using the SQL storage backend")
    global _engine, _session_factory
    with _lock:
        if _engine is None or _session_factory is None:
            _engine = create_engine(
                database_url,
                future=True,
                pool_pre_ping=True,
            )
            _session_factory = sessionmaker(
                bind=_engine,
                class_=Session,
                autoflush=False,
                expire_on_commit=False,
            )
    assert _engine is not None
    assert _session_factory is not None
    return _engine, _session_factory


def get_sessionmaker(database_url: str) -> sessionmaker[Session]:
    """Return the configured session factory for the provided database URL."""
    _, session_factory = configure_engine(database_url)
    return session_factory


@contextmanager
def get_session(database_url: str) -> Iterator[Session]:
    """Provide a short-lived Session suitable for scripts or background jobs."""
    session_factory = get_sessionmaker(database_url)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
