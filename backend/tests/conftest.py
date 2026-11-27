"""Shared test setup: an in-memory SQLite database filled with the sample data.

The API code is database-agnostic, so tests run without PostgreSQL (also in CI).
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.db import get_db
from app.main import app
from app.models import Base
from app.seed import seed

# The test client talks plain http://testserver, a Secure cookie would never be sent back.
settings.cookie_secure = False


@pytest.fixture(scope="session")
def session_factory() -> sessionmaker[Session]:
    # StaticPool keeps one connection, so every session sees the same in-memory database.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
    return factory


@pytest.fixture
def db(session_factory) -> Iterator[Session]:
    with session_factory() as session:
        yield session


def _use_database(factory: sessionmaker[Session]) -> None:
    """Point the app's get_db dependency at the given test database."""

    def override_get_db() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client(session_factory) -> Iterator[TestClient]:
    _use_database(session_factory)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def empty_factory() -> Iterator[sessionmaker[Session]]:
    """A fresh empty database for one test (for tests that change data)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    _use_database(factory)
    yield factory
    app.dependency_overrides.clear()
