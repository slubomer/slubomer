"""Editorial API: promises, evidence, documents, categories, glossary."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuditLog, Subject, Verdict
from app.models.enums import UserRole, VerdictState, VerdictValue
from tests.test_auth import login, make_user

API = "/api/v1/admin"
NEW_PROMISE = {
    "subject": "strana",
    "title": "Nové cyklotrasy",
    "description": "Postavíme 100 km cyklotrás.",
}


@pytest.fixture
def editor(empty_factory) -> TestClient:
    """Logged-in editor (redaktor) and one subject in the database."""
    with empty_factory() as db:
        db.add(Subject(slug="strana", name="Strana"))
        db.commit()
    make_user(empty_factory, "r@example.com", UserRole.REDAKTOR)
    return login("r@example.com")


def audit_entries(factory, entity: str) -> list[AuditLog]:
    with factory() as db:
        return list(db.scalars(select(AuditLog).where(AuditLog.entity == entity)))


def new_document(editor: TestClient) -> int:
    document = {"kind": "program", "title": "Volebný program", "url": "https://example.com/p.pdf"}
    response = editor.post(f"{API}/documents", json=document)
    assert response.status_code == 201
    return response.json()["id"]


def sourced_promise(editor: TestClient) -> dict:
    """Body of a new promise with everything approval needs: quote, page and document."""
    return {**NEW_PROMISE, "document_id": new_document(editor), "quote": "100 km", "page": 3}


def test_new_promise_is_public_only_after_approval(editor, empty_factory):
    created = editor.post(f"{API}/promises", json=sourced_promise(editor))
    assert created.status_code == 201
    promise = created.json()
    assert promise["state"] == "navrh" and promise["slug"] == "nove-cyklotrasy"

    public = TestClient(app)
    assert public.get("/api/v1/promises/nove-cyklotrasy").status_code == 404

    approved = editor.post(f"{API}/promises/{promise['id']}/approve")
    assert approved.json()["state"] == "schvaleny"
    assert public.get("/api/v1/promises/nove-cyklotrasy").status_code == 200
    # Approving twice makes no sense.
    assert editor.post(f"{API}/promises/{promise['id']}/approve").status_code == 409

    actions = [e.action for e in audit_entries(empty_factory, "promise")]
    assert actions == ["create", "approve"]


def test_approval_needs_quote_page_and_document(editor):
    promise_id = editor.post(f"{API}/promises", json=NEW_PROMISE).json()["id"]

    refused = editor.post(f"{API}/promises/{promise_id}/approve")
    assert refused.status_code == 422
    assert "citácia" in refused.json()["detail"] and "dokument" in refused.json()["detail"]

    filled = {"document_id": new_document(editor), "quote": "100 km", "page": 3}
    editor.patch(f"{API}/promises/{promise_id}", json=filled)
    assert editor.post(f"{API}/promises/{promise_id}/approve").status_code == 200


def test_reject_needs_reason_and_hides_promise(editor, empty_factory):
    promise_id = editor.post(f"{API}/promises", json=sourced_promise(editor)).json()["id"]
    editor.post(f"{API}/promises/{promise_id}/approve")

    assert editor.post(f"{API}/promises/{promise_id}/reject", json={}).status_code == 422
    rejected = editor.post(f"{API}/promises/{promise_id}/reject", json={"reason": "Nie je to sľub"})

    assert rejected.json()["state"] == "zamietnuty"
    assert TestClient(app).get("/api/v1/promises/nove-cyklotrasy").status_code == 404
    # The admin list still shows it, so nothing disappears silently.
    listed = editor.get(f"{API}/promises", params={"state": "zamietnuty"}).json()
    assert listed["total"] == 1
    assert audit_entries(empty_factory, "promise")[-1].reason == "Nie je to sľub"


def test_changing_filled_quote_needs_reason(editor, empty_factory):
    promise_id = editor.post(f"{API}/promises", json=NEW_PROMISE).json()["id"]
    url = f"{API}/promises/{promise_id}"

    # The first quote may be filled in freely.
    assert editor.patch(url, json={"quote": "Postavíme 100 km", "page": 4}).status_code == 200
    # Changing it afterwards needs a reason.
    assert editor.patch(url, json={"quote": "Postavíme 200 km"}).status_code == 422
    assert editor.patch(url, json={"page": 5}).status_code == 422
    fixed = editor.patch(url, json={"page": 5, "reason": "Preklep v čísle strany"})

    assert fixed.status_code == 200 and fixed.json()["page"] == 5
    last = audit_entries(empty_factory, "promise")[-1]
    assert (last.before, last.after, last.reason) == (
        {"page": 4},
        {"page": 5},
        "Preklep v čísle strany",
    )


def test_update_changes_category_and_search(editor):
    category = editor.post(f"{API}/categories", json={"label": "Doprava"}).json()
    promise_id = editor.post(f"{API}/promises", json=sourced_promise(editor)).json()["id"]
    editor.post(f"{API}/promises/{promise_id}/approve")

    updated = editor.patch(
        f"{API}/promises/{promise_id}", json={"category": "doprava", "title": "Cyklochodníky"}
    ).json()

    assert updated["category"]["slug"] == category["slug"] == "doprava"
    assert updated["slug"] == "nove-cyklotrasy"  # the public link stays the same
    # Search finds the promise by its new title and by its category.
    for q in ("cyklochodniky", "doprava"):
        assert TestClient(app).get("/api/v1/promises", params={"q": q}).json()["total"] == 1
    assert editor.get(f"{API}/promises", params={"without_category": True}).json()["total"] == 0


def test_required_fields_cannot_be_cleared(editor):
    promise_id = editor.post(f"{API}/promises", json=NEW_PROMISE).json()["id"]

    assert editor.patch(f"{API}/promises/{promise_id}", json={"title": None}).status_code == 422
    assert (
        editor.patch(f"{API}/promises/{promise_id}", json={"category": "neexistuje"}).status_code
        == 422
    )


def test_evidence_add_and_delete_with_reason(editor, empty_factory):
    promise_id = editor.post(f"{API}/promises", json=NEW_PROMISE).json()["id"]
    document_id = new_document(editor)

    detail = editor.post(
        f"{API}/promises/{promise_id}/evidence",
        json={"document_id": document_id, "role": "zdroj", "quote": "100 km cyklotrás", "page": 12},
    ).json()
    (evidence,) = detail["evidence"]
    assert evidence["document"]["title"] == "Volebný program"

    url = f"{API}/promises/{promise_id}/evidence/{evidence['id']}"
    assert editor.delete(url).status_code == 422  # no reason
    deleted = editor.delete(url, params={"reason": "Nesprávny dokument"})

    assert deleted.json()["evidence"] == []
    removed = audit_entries(empty_factory, "evidence")[-1]
    assert removed.action == "delete" and removed.before["quote"] == "100 km cyklotrás"


def test_evidence_of_published_verdict_cannot_be_deleted(editor, empty_factory):
    promise_id = editor.post(f"{API}/promises", json=NEW_PROMISE).json()["id"]
    document_id = new_document(editor)
    added = {"document_id": document_id, "quote": "Zákon prijatý", "page": 1}
    detail = editor.post(
        f"{API}/promises/{promise_id}/evidence", json={**added, "role": "podklad"}
    ).json()
    detail = editor.post(
        f"{API}/promises/{promise_id}/evidence", json={**added, "role": "zdroj"}
    ).json()
    basis, source = detail["evidence"]
    with empty_factory() as db:
        db.add(
            Verdict(
                promise_id=promise_id,
                version=1,
                value=VerdictValue.SPLNENE,
                explanation="Zákon bol prijatý.",
                state=VerdictState.PUBLIKOVANY,
            )
        )
        db.commit()

    url = f"{API}/promises/{promise_id}/evidence"
    reason = {"reason": "Skúška"}
    assert editor.delete(f"{url}/{basis['id']}", params=reason).status_code == 409
    # Where the promise was made (zdroj) is not what the verdict rests on.
    assert editor.delete(f"{url}/{source['id']}", params=reason).status_code == 200


def test_verifier_reads_but_cannot_change(editor, empty_factory):
    promise_id = editor.post(f"{API}/promises", json=NEW_PROMISE).json()["id"]
    make_user(empty_factory, "o@example.com", UserRole.OVEROVATEL)
    verifier = login("o@example.com")

    assert verifier.get(f"{API}/promises/{promise_id}").status_code == 200
    assert verifier.post(f"{API}/promises/{promise_id}/approve").status_code == 403
    assert verifier.post(f"{API}/categories", json={"label": "Doprava"}).status_code == 403
    assert TestClient(app).get(f"{API}/promises").status_code == 401


def test_categories_and_glossary(editor, empty_factory):
    category_id = editor.post(f"{API}/categories", json={"label": "Doprava"}).json()["id"]
    assert editor.post(f"{API}/categories", json={"label": "Doprava"}).status_code == 409
    renamed = editor.patch(f"{API}/categories/{category_id}", json={"label": "Doprava a cesty"})
    assert renamed.json() == {
        "id": category_id,
        "slug": "doprava",
        "label": "Doprava a cesty",
        "tagline": None,
    }

    term = {"name": "Koalícia", "short": "Spojenie strán", "example": "Vládna koalícia"}
    term_id = editor.post(f"{API}/glossary", json=term).json()["id"]
    editor.patch(f"{API}/glossary/{term_id}", json={"stems": ["koalíci"]})
    public = TestClient(app).get("/api/v1/glossary/koalicia").json()

    assert public["stems"] == ["koalíci"]
    assert [e.action for e in audit_entries(empty_factory, "glossary_term")] == ["create", "update"]


def test_documents_need_valid_url(editor):
    bad = {"kind": "program", "title": "Program", "url": "nie-je-url"}
    assert editor.post(f"{API}/documents", json=bad).status_code == 422
    new_document(editor)
    assert [d["title"] for d in editor.get(f"{API}/documents").json()] == ["Volebný program"]
