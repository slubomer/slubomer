"""Verification of published AI verdicts by a political scientist (B-12)."""

import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuditLog, Promise, Verdict
from app.models.enums import UserRole, VerdictState
from app.schemas.promise_import import PromiseImportFile
from app.services.promise_import_service import import_file
from tests.test_auth import login, make_user
from tests.test_import_promises import FILE

API = "/api/v1/admin/verdicts"


def web_only_file() -> dict:
    """The "splnene" promise rests only on a news article."""
    data = copy.deepcopy(FILE)
    data["sluby"][1]["vyhodnotenie"] = [data["sluby"][1]["vyhodnotenie"][1]]
    return data


@pytest.fixture
def imported(empty_factory):
    """Factory with the sample file imported: AI verdicts already public."""

    def load(data: dict = FILE):
        with empty_factory() as db:
            import_file(db, PromiseImportFile.model_validate(data))

    return load


@pytest.fixture
def verifier(empty_factory) -> TestClient:
    make_user(empty_factory, "o@example.com", UserRole.OVEROVATEL)
    return login("o@example.com")


def current_verdict(client: TestClient, slug: str) -> dict:
    items = client.get(API, params={"verified": "false"}).json()["items"]
    return next(v for v in items if v["promise"]["slug"] == slug)


def test_queue_lists_unverified_ai_verdicts(imported, verifier):
    imported()

    page = verifier.get(API, params={"verified": "false"}).json()

    assert page["total"] == 2
    assert {v["promise"]["slug"] for v in page["items"]} == {"nove-cyklotrasy", "lacnejsie-lieky"}
    assert all(v["state"] == "publikovany" and not v["verified"] for v in page["items"])
    assert verifier.get(API, params={"verified": "true"}).json()["total"] == 0


def test_verify_publishes_new_version_marked_verified(imported, verifier, empty_factory):
    imported()
    verdict = current_verdict(verifier, "lacnejsie-lieky")

    response = verifier.post(
        f"{API}/{verdict['id']}/verify", json={"reason": "Zákon som skontroloval v Slov-Lexe."}
    )

    assert response.status_code == 200
    versions = response.json()["verdicts"]  # newest first
    assert [(v["version"], v["state"], v["verified"]) for v in versions] == [
        (2, "publikovany", True),
        (1, "nahradeny", False),
    ]
    # Unchanged text keeps the AI label and confidence.
    assert (versions[0]["ai_generated"], versions[0]["confidence"]) == (True, 0.85)
    assert versions[0]["reviewer_role"] == "politológ"

    public = TestClient(app).get("/api/v1/promises/lacnejsie-lieky").json()
    assert public["verdict"]["verified"] is True
    assert [v["verified"] for v in public["history"]] == [True, False]
    with empty_factory() as db:
        entry = db.scalar(select(AuditLog).where(AuditLog.action == "verify"))
        assert entry.reason == "Zákon som skontroloval v Slov-Lexe."
        assert entry.before["value"] == "splnene"


def test_verify_can_correct_value_and_text(imported, verifier):
    imported()
    verdict = current_verdict(verifier, "lacnejsie-lieky")

    body = {
        "reason": "Zákon rieši len časť sľubu.",
        "value": "ciastocne",
        "explanation": "Splnená je len časť sľubu, doplatky sa znížili iba pre seniorov.",
    }
    latest = verifier.post(f"{API}/{verdict['id']}/verify", json=body).json()["verdicts"][0]

    assert (latest["value"], latest["verified"]) == ("ciastocne", True)
    # The text is no longer the AI's.
    assert (latest["ai_generated"], latest["confidence"]) == (False, None)


def test_verify_needs_reason(imported, verifier):
    imported()
    verdict = current_verdict(verifier, "lacnejsie-lieky")

    assert verifier.post(f"{API}/{verdict['id']}/verify", json={}).status_code == 422
    assert verifier.post(f"{API}/{verdict['id']}/verify", json={"reason": ""}).status_code == 422


def test_news_article_is_not_enough_to_verify(imported, verifier):
    imported(web_only_file())
    verdict = current_verdict(verifier, "lacnejsie-lieky")

    response = verifier.post(f"{API}/{verdict['id']}/verify", json={"reason": "Súhlasím."})

    assert response.status_code == 422
    assert "publikovaného dokumentu" in response.json()["detail"]
    # The AI verdict itself stays public, it only can't be marked as verified.
    assert TestClient(app).get("/api/v1/promises/lacnejsie-lieky").status_code == 200


def test_not_kept_needs_no_evidence(imported, verifier):
    imported()
    verdict = current_verdict(verifier, "nove-cyklotrasy")  # "nesplnene", no evidence

    response = verifier.post(f"{API}/{verdict['id']}/verify", json={"reason": "Nič sa nenašlo."})

    assert response.status_code == 200


def test_internal_value_cannot_be_verified(imported, verifier):
    imported()
    verdict = current_verdict(verifier, "nove-cyklotrasy")

    body = {"reason": "Neviem posúdiť.", "value": "nedostatok_informacii"}
    assert verifier.post(f"{API}/{verdict['id']}/verify", json=body).status_code == 422


def test_verifying_twice_without_change_conflicts(imported, verifier):
    imported()
    verdict = current_verdict(verifier, "lacnejsie-lieky")
    new = verifier.post(f"{API}/{verdict['id']}/verify", json={"reason": "Sedí to."}).json()
    new_id = new["verdicts"][0]["id"]

    again = verifier.post(f"{API}/{new_id}/verify", json={"reason": "Sedí to."})
    old = verifier.post(f"{API}/{verdict['id']}/verify", json={"reason": "Sedí to."})

    assert again.status_code == 409
    assert old.status_code == 409  # replaced versions are history


def test_only_political_scientist_verifies(imported, empty_factory):
    imported()
    make_user(empty_factory, "r@example.com", UserRole.REDAKTOR)
    editor = login("r@example.com")
    verdict_id = editor.get(API).json()["items"][0]["id"]  # the editor may read the queue

    assert editor.post(f"{API}/{verdict_id}/verify", json={"reason": "Sedí."}).status_code == 403
    anonymous = TestClient(app)
    assert anonymous.post(f"{API}/{verdict_id}/verify", json={"reason": "x"}).status_code == 401
    assert anonymous.get(API).status_code == 401


def test_comment_is_not_verification(imported, verifier, empty_factory):
    imported()
    with empty_factory() as db:
        promise_id = db.scalar(select(Promise.id).where(Promise.slug == "lacnejsie-lieky"))

    verifier.post(f"/api/v1/admin/promises/{promise_id}/comments", json={"text": "Poznámka."})

    public = TestClient(app).get("/api/v1/promises/lacnejsie-lieky").json()
    assert public["explained"] is True
    assert public["verdict"]["verified"] is False
    with empty_factory() as db:
        assert db.scalar(select(Verdict.state).where(Verdict.promise_id == promise_id)) == (
            VerdictState.PUBLIKOVANY
        )


def test_public_list_filters_verified(imported, verifier):
    imported()
    verdict = current_verdict(verifier, "lacnejsie-lieky")
    verifier.post(f"{API}/{verdict['id']}/verify", json={"reason": "Sedí to."})

    public = TestClient(app)
    verified = public.get("/api/v1/promises", params={"verified": "true"}).json()["items"]
    ai_only = public.get("/api/v1/promises", params={"verified": "false"}).json()["items"]

    assert [i["slug"] for i in verified] == ["lacnejsie-lieky"]
    assert [i["slug"] for i in ai_only] == ["nove-cyklotrasy"]
