"""FastAPI dependencies: read-only database session.

The API never writes. If ``READ_ONLY_DATABASE_URL`` is configured it is used
(recommended: a least-privilege role with SELECT only); otherwise it falls back
to ``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from rera.config import get_settings
from rera.database.session import create_db_engine, create_session_factory

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.read_only_database_url or settings.database_url
        _engine = create_db_engine(url)
    return _engine


def get_session() -> Iterator[Session]:
    factory = create_session_factory(get_engine())
    session = factory()
    try:
        yield session
    finally:
        session.close()
