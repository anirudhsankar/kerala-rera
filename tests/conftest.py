"""Shared pytest fixtures.

Tests run against an in-memory SQLite database so they are deterministic and
never touch a production PostgreSQL instance.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from rera.database.models import Base

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "sample"


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def session(engine) -> Session:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    db = factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def sample_path() -> Path:
    return SAMPLE_DIR / "projects_sample.csv"


@pytest.fixture()
def sample_modified_path() -> Path:
    return SAMPLE_DIR / "projects_sample_modified.csv"


@pytest.fixture()
def sample_duplicate_path() -> Path:
    return SAMPLE_DIR / "projects_duplicate_sample.csv"
