"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from rera.config import get_settings
from rera.database.models import Base


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine.

    SQLite in-memory databases use a ``StaticPool`` so that multiple
    connections within a test share the same database.
    """

    url = database_url or get_settings().database_url
    connect_args: dict = {}
    engine_kwargs: dict = {"future": True, "pool_pre_ping": True}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in url:
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db(engine: Engine | None = None) -> Engine:
    """Create all tables (convenience for dev/tests; production uses Alembic)."""

    engine = engine or create_db_engine()
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope(
    engine: Engine | None = None, *, commit: bool = True
) -> Iterator[Session]:
    """Provide a transactional session scope.

    On success the transaction is committed (unless ``commit=False``) and on
    error it is rolled back.
    """

    engine = engine or create_db_engine()
    factory = create_session_factory(engine)
    session = factory()
    try:
        yield session
        if commit:
            session.commit()
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
