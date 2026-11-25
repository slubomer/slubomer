"""Import of real promises (format of data/sluby.json) into a fresh database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.import_promises import import_promises
from app.main import app
from app.models import Base, Promise, Subject, Verdict
from app.models.enums import PromiseState

RECORDS = [
    {
        "strana": "Strana Jedna – demokrati",
        "nazov": "Nové cyklotrasy",
        "telo": "Vybudujeme nové cyklotrasy v regiónoch.",
        "datum": None,
        "stav": "nesplnene",
    },
    {
        "strana": "Strana Jedna – demokrati",
        "nazov": "Lacnejšie lieky",
        "telo": "Znížime doplatky za lieky.",
        "datum": None,
        "stav": "nesplnene",
    },
    # Same text as above, different title: a duplicate, skipped.
    {
        "strana": "Strana Jedna – demokrati",
        "nazov": "Nižšie doplatky",
        "telo": "Znížime doplatky za lieky.",
        "datum": None,
        "stav": "nesplnene",
    },
    # Same title as the first one, other party: a separate promise with its own slug.
    {
        "strana": "Hnutie Dva",
        "nazov": "Nové cyklotrasy",
        "telo": "Postavíme 100 km cyklotrás.",
        "datum": None,
        "stav": "nesplnene",
    },
]


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_import_creates_subjects_and_promises_without_verdict(factory):
    with factory() as db:
        result = import_promises(db, RECORDS)

        assert (result.created, result.skipped) == (3, 1)
        subjects = {s.slug: s for s in db.scalars(select(Subject))}
        assert set(subjects) == {"strana-jedna-demokrati", "hnutie-dva"}
        assert subjects["strana-jedna-demokrati"].short_name == "Strana Jedna"
        assert subjects["hnutie-dva"].short_name is None
        assert set(db.scalars(select(Promise.slug))) == {
            "nove-cyklotrasy",
            "lacnejsie-lieky",
            "nove-cyklotrasy-hnutie-dva",
        }
        # "stav" is only a placeholder: no verdicts are created.
        assert db.scalar(select(func.count(Verdict.id))) == 0


def test_import_is_idempotent(factory):
    with factory() as db:
        import_promises(db, RECORDS)
        result = import_promises(db, RECORDS)

        assert (result.created, result.skipped) == (0, 4)
        assert db.scalar(select(func.count(Promise.id))) == 3


def test_imported_promises_are_drafts(factory):
    """Without a quote and source they must not reach the public web."""
    with factory() as db:
        import_promises(db, RECORDS)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        items = client.get("/api/v1/promises", params={"q": "cyklotrasy"}).json()["items"]
        detail = client.get("/api/v1/promises/lacnejsie-lieky")
        stats = client.get("/api/v1/stats/overview").json()
    finally:
        app.dependency_overrides.clear()

    assert items == []
    assert detail.status_code == 404
    assert stats["total"] == 0
    with factory() as db:
        states = set(db.scalars(select(Promise.state)))
    assert states == {PromiseState.NAVRH}
