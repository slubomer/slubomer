"""Import of promises from JSON (format of data/sluby.json): service, API and real file."""

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import (
    AuditLog,
    Base,
    Category,
    Document,
    Evidence,
    Promise,
    Subject,
    User,
    Verdict,
)
from app.models.enums import (
    DocumentKind,
    PromiseState,
    PromiseType,
    UserRole,
    VerdictState,
    VerdictValue,
)
from app.schemas.promise_import import PromiseImportFile
from app.services import verdict_service
from app.services.promise_import_service import import_file
from tests.test_auth import login, make_user

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "sluby.json"
VOTE_URL = "https://www.nrsr.sk/web/Default.aspx?sid=schodze/hlasovanie/hlasklub&ID=1"

FILE = {
    "meta": {"schema_verzia": "2.0", "generovane_ai": True, "aktualizovane": "2026-11-26"},
    "sluby": [
        {
            "strana": "Strana Jedna – demokrati",
            "nazov": "Nové cyklotrasy",
            "telo": "Vybudujeme nové cyklotrasy v regiónoch.",
            "citacia": "Vybudujeme cyklotrasy.",
            "strana_programu": 4,
            "zdroj": "Program Strany Jedna",
            "program_url": None,
            "tema": "Doprava",
            "typ": "stavba",
            "stav": "nesplnene",
            "zdovodnenie": "Nenašiel sa žiadny dôkaz o začatí plnenia.",
            "confidence": 0.4,
            "vyhodnotenie": [],
        },
        {
            "strana": "Strana Jedna – demokrati",
            "nazov": "Lacnejšie lieky",
            "telo": "Znížime doplatky za lieky.",
            "citacia": "Znížime doplatky.",
            "strana_programu": 7,
            "zdroj": "Program Strany Jedna",
            "tema": "Zdravotníctvo",
            "typ": "zakon",
            "stav": "splnene",
            "zdovodnenie": "Zákon prešiel (Za 80 zo 140 prítomných).",
            "confidence": 0.85,
            "vyhodnotenie": [
                {
                    "typ": "hlasovanie",
                    "zdroj": VOTE_URL,
                    "datum": "2024-02-13",
                    "hlasovanie": {
                        "faza": "finalne",
                        "vysledok": "Návrh prešiel",
                        "strana_za": 20,
                        "clenov_strany": 21,
                        "celkom_za": 80,
                        "pritomnych": 140,
                    },
                },
                {"typ": "web", "zdroj": "https://www.teraz.sk/clanok", "datum": "2024-03-01"},
            ],
        },
        # Same text as above, different title: a duplicate, skipped.
        {
            "strana": "Strana Jedna – demokrati",
            "nazov": "Nižšie doplatky",
            "telo": "Znížime doplatky za lieky.",
        },
        # Same title as the first one, other party: a separate promise with its own slug.
        {"strana": "Hnutie Dva", "nazov": "Nové cyklotrasy", "telo": "Postavíme 100 km cyklotrás."},
    ],
}


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def make_verifier(db) -> User:
    user = User(
        email="o@example.com", name="Politológ", role=UserRole.OVEROVATEL, password_hash="x"
    )
    db.add(user)
    db.flush()
    return user


def run(db, data: dict = FILE):
    return import_file(db, PromiseImportFile.model_validate(data), source="test")


def test_import_fills_promise_fields_and_subjects(factory):
    with factory() as db:
        result = run(db)

        assert (result.created, result.skipped) == (3, 1)
        subjects = {s.slug: s for s in db.scalars(select(Subject))}
        assert subjects["strana-jedna-demokrati"].short_name == "Strana Jedna"
        assert subjects["hnutie-dva"].short_name is None
        assert set(db.scalars(select(Promise.slug))) == {
            "nove-cyklotrasy",
            "lacnejsie-lieky",
            "nove-cyklotrasy-hnutie-dva",
        }

        promise = db.scalar(select(Promise).where(Promise.slug == "lacnejsie-lieky"))
        assert (promise.quote, promise.page, promise.type) == (
            "Znížime doplatky.",
            7,
            PromiseType.ZAKON,
        )
        # It has a quote, page and programme, so it is public right away.
        assert promise.state == PromiseState.SCHVALENY
        assert promise.ai_generated is True
        # Without a source a promise stays a draft for the editors.
        unsourced = db.scalar(select(Promise).where(Promise.slug == "nove-cyklotrasy-hnutie-dva"))
        assert unsourced.state == PromiseState.NAVRH
        assert promise.category.label == "Zdravotníctvo"
        assert promise.document.kind == DocumentKind.PROGRAM
        assert promise.document.title == "Program Strany Jedna"
        # Both promises of the party share one programme document.
        assert db.scalar(select(func.count(Document.id)).where(Document.kind == "program")) == 1
        assert {c.slug for c in db.scalars(select(Category))} == {"doprava", "zdravotnictvo"}


def test_import_publishes_ai_verdicts_with_json_states(factory):
    with factory() as db:
        run(db)

        verdicts = {v.promise.slug: v for v in db.scalars(select(Verdict))}
        assert set(verdicts) == {"nove-cyklotrasy", "lacnejsie-lieky"}  # no "stav", no verdict
        verdict = verdicts["lacnejsie-lieky"]
        assert verdict.value == VerdictValue.SPLNENE
        assert verdict.state == VerdictState.PUBLIKOVANY and verdict.published_at is not None
        assert (verdict.version, verdict.confidence, verdict.ai_generated) == (1, 0.85, True)
        assert verdict.verified is False  # only AI so far
        # "nesplnene" says no evidence was found, so it is published without any.
        assert verdicts["nove-cyklotrasy"].state == VerdictState.PUBLIKOVANY


def test_verdict_without_evidence_stays_draft(factory):
    data = copy.deepcopy(FILE)
    data["sluby"][1]["vyhodnotenie"] = []  # "splnene" with nothing behind it

    with factory() as db:
        run(db, data)

        verdict = db.scalar(select(Verdict).where(Verdict.value == VerdictValue.SPLNENE))
        assert verdict.state == VerdictState.NAVRH and verdict.published_at is None


def test_import_stores_votes_and_web_pages_as_evidence(factory):
    with factory() as db:
        result = run(db)

        assert result.evidence == 2
        rows = db.scalars(select(Evidence).order_by(Evidence.id)).all()
        vote, web = rows
        assert vote.document.kind == DocumentKind.HLASOVANIE
        assert vote.document.url == VOTE_URL
        assert vote.document.title == "Hlasovanie NR SR 13. 02. 2024"
        assert vote.vote["strana_za"] == 20 and vote.quote is None
        assert web.document.kind == DocumentKind.WEB
        assert web.document.title == "teraz.sk" and web.vote is None


def test_reimport_changes_nothing(factory):
    with factory() as db:
        run(db)
        result = run(db)

        assert (result.created, result.updated, result.skipped) == (0, 0, 4)
        assert (result.verdicts, result.evidence) == (0, 0)
        assert db.scalar(select(func.count(Promise.id))) == 3
        assert db.scalar(select(func.count(Verdict.id))) == 2
        assert db.scalar(select(func.count(Evidence.id))) == 2


def test_reimport_with_new_state_adds_verdict_version(factory):
    newer = copy.deepcopy(FILE)
    newer["sluby"][1]["stav"] = "ciastocne"
    newer["sluby"][1]["zdovodnenie"] = "Splnená je len časť sľubu."

    with factory() as db:
        run(db)
        result = run(db, newer)

        assert (result.updated, result.verdicts) == (1, 1)
        promise = db.scalar(select(Promise).where(Promise.slug == "lacnejsie-lieky"))
        versions = sorted(((v.version, v.value, v.state) for v in promise.verdicts), reverse=True)
        assert versions == [
            (2, VerdictValue.CIASTOCNE, VerdictState.PUBLIKOVANY),
            (1, VerdictValue.SPLNENE, VerdictState.NAHRADENY),
        ]


def test_reimport_never_replaces_verified_verdict(factory):
    newer = copy.deepcopy(FILE)
    newer["sluby"][1]["stav"] = "ciastocne"
    newer["sluby"][1]["zdovodnenie"] = "Splnená je len časť sľubu."

    with factory() as db:
        run(db)
        verdict = db.scalar(select(Verdict).where(Verdict.value == VerdictValue.SPLNENE))
        verdict_service.verify(db, make_verifier(db), verdict.id, "Zákon som skontroloval.")
        run(db, newer)

        promise = db.scalar(select(Promise).where(Promise.slug == "lacnejsie-lieky"))
        states = sorted(((v.version, v.value, v.state) for v in promise.verdicts), reverse=True)
        # The new AI result waits as a draft, the verified version stays public.
        assert states == [
            (3, VerdictValue.CIASTOCNE, VerdictState.NAVRH),
            (2, VerdictValue.SPLNENE, VerdictState.PUBLIKOVANY),
            (1, VerdictValue.SPLNENE, VerdictState.NAHRADENY),
        ]


def test_reimport_fills_only_empty_fields(factory):
    older = copy.deepcopy(FILE)
    for record in older["sluby"]:
        record.pop("tema", None)
    changed = copy.deepcopy(FILE)
    changed["sluby"][1]["citacia"] = "Iný text citácie."

    with factory() as db:
        run(db, older)
        result = run(db, changed)

        assert result.updated == 2  # both promises of the first party got a category
        promise = db.scalar(select(Promise).where(Promise.slug == "lacnejsie-lieky"))
        assert promise.category.label == "Zdravotníctvo"
        assert promise.quote == "Znížime doplatky."  # a filled-in quote is never overwritten


def test_imported_promises_are_public_as_ai_verdicts(factory):
    with factory() as db:
        run(db)

    from tests.conftest import _use_database

    _use_database(factory)
    try:
        client = TestClient(app)
        items = client.get("/api/v1/promises", params={"q": "cyklotrasy"}).json()["items"]
        detail = client.get("/api/v1/promises/lacnejsie-lieky")
        stats = client.get("/api/v1/stats/overview").json()
    finally:
        app.dependency_overrides.clear()

    # The party with a source is public, the one without stays hidden.
    assert [i["slug"] for i in items] == ["nove-cyklotrasy"]
    assert detail.status_code == 200
    verdict = detail.json()["verdict"]
    assert verdict["value"] == "splnene"
    assert (verdict["ai_generated"], verdict["verified"]) == (True, False)
    assert detail.json()["evidence"][0]["vote"]["celkom_za"] == 80
    assert stats["total"] == 2 and stats["unrated"] == 0


# --- Editorial API ------------------------------------------------------------


@pytest.fixture
def editor(empty_factory) -> TestClient:
    make_user(empty_factory, "r@example.com", UserRole.REDAKTOR)
    return login("r@example.com")


def test_api_import_and_audit(editor, empty_factory):
    response = editor.post("/api/v1/admin/promises/import", json=FILE)

    assert response.status_code == 200
    assert response.json() == {
        "created": 3,
        "updated": 0,
        "skipped": 1,
        "verdicts": 2,
        "evidence": 2,
    }
    listed = editor.get("/api/v1/admin/promises", params={"state": "schvaleny"}).json()
    assert listed["total"] == 2
    with empty_factory() as db:
        entry = db.scalar(select(AuditLog).where(AuditLog.action == "import"))
        assert entry.actor_id is not None
        assert entry.after["meta"]["schema_verzia"] == "2.0"


def test_api_invalid_file_saves_nothing(editor, empty_factory):
    broken = copy.deepcopy(FILE)
    broken["sluby"][0]["stav"] = "v_procese"  # not one of the four states
    broken["sluby"][1]["vyhodnotenie"][0].pop("hlasovanie")
    broken["sluby"][3]["zdovodnenie"] = None
    broken["sluby"][3]["stav"] = "splnene"  # a state needs a reason

    response = editor.post("/api/v1/admin/promises/import", json=broken)

    assert response.status_code == 422
    locations = [error["loc"][:3] for error in response.json()["detail"]]
    assert ["body", "sluby", 0] in locations
    assert ["body", "sluby", 1] in locations
    assert ["body", "sluby", 3] in locations
    with empty_factory() as db:
        assert db.scalar(select(func.count(Promise.id))) == 0


def test_api_import_needs_editor(empty_factory):
    assert TestClient(app).post("/api/v1/admin/promises/import", json=FILE).status_code == 401
    make_user(empty_factory, "o@example.com", UserRole.OVEROVATEL)
    verifier = login("o@example.com")
    assert verifier.post("/api/v1/admin/promises/import", json=FILE).status_code == 403


# --- The real file ------------------------------------------------------------


def test_data_file_is_valid_and_uses_four_states():
    data = PromiseImportFile.model_validate(json.loads(DATA_FILE.read_text(encoding="utf-8")))

    assert len(data.sluby) > 0
    states = {record.stav for record in data.sluby}
    assert states <= {
        VerdictValue.SPLNENE,
        VerdictValue.CIASTOCNE,
        VerdictValue.PORUSENE,
        VerdictValue.NESPLNENE,
    }
