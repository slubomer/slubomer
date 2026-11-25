"""Political scientists' comments on promises and who may edit the glossary."""

import pyotp
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import UserRole
from tests.test_admin_promises import API, audit_entries, editor, sourced_promise  # noqa: F401
from tests.test_auth import login, make_user

PUBLIC = "/api/v1/promises/nove-cyklotrasy"
TERM = {"name": "Koalícia", "short": "Spojenie strán.", "example": "Vládna koalícia."}


@pytest.fixture
def promise_id(editor) -> int:  # noqa: F811
    """An approved (public) promise, created by the editor."""
    promise_id = editor.post(f"{API}/promises", json=sourced_promise(editor)).json()["id"]
    editor.post(f"{API}/promises/{promise_id}/approve")
    return promise_id


@pytest.fixture
def verifier(empty_factory) -> TestClient:
    make_user(empty_factory, "p@example.com", UserRole.OVEROVATEL)
    return login("p@example.com")


def comments_url(promise_id: int) -> str:
    return f"{API}/promises/{promise_id}/comments"


def test_promise_shows_every_comment_and_is_explained(verifier, promise_id, empty_factory):
    public = TestClient(app)
    assert public.get(PUBLIC).json()["explained"] is False

    verifier.post(comments_url(promise_id), json={"text": "Prvé vysvetlenie."})
    detail = verifier.post(comments_url(promise_id), json={"text": "Doplnenie."})
    assert detail.status_code == 201
    assert [c["text"] for c in detail.json()["comments"]] == ["Prvé vysvetlenie.", "Doplnenie."]

    shown = public.get(PUBLIC).json()
    assert shown["explained"] is True
    assert [c["text"] for c in shown["comments"]] == ["Prvé vysvetlenie.", "Doplnenie."]
    # Role only, no name or account id on the public web.
    assert shown["comments"][0]["author_role"] == "politológ"
    assert "author_id" not in shown["comments"][0]
    # The list shows the flag too, so the web can label the card.
    (item,) = public.get("/api/v1/promises").json()["items"]
    assert item["explained"] is True
    # A comment does not mean the verdict was approved by a political scientist.
    assert shown["verdict"] is None

    assert [e.action for e in audit_entries(empty_factory, "promise_comment")] == [
        "create",
        "create",
    ]


def test_author_edits_and_deletes_own_comment(verifier, promise_id, empty_factory):
    comment_id = verifier.post(comments_url(promise_id), json={"text": "Pôvodne"}).json()[
        "comments"
    ][0]["id"]
    url = f"{comments_url(promise_id)}/{comment_id}"

    edited = verifier.patch(url, json={"text": "Opravené"}).json()["comments"][0]
    assert edited["text"] == "Opravené" and edited["updated_at"] is not None

    assert verifier.delete(url).json()["comments"] == []
    assert TestClient(app).get(PUBLIC).json()["explained"] is False

    entries = audit_entries(empty_factory, "promise_comment")
    assert [e.action for e in entries] == ["create", "update", "delete"]
    assert entries[-1].before["text"] == "Opravené"  # the deleted text can be restored


def test_only_the_author_may_change_a_comment(verifier, promise_id, empty_factory):
    comment_id = verifier.post(comments_url(promise_id), json={"text": "Môj"}).json()["comments"][
        0
    ]["id"]
    url = f"{comments_url(promise_id)}/{comment_id}"

    make_user(empty_factory, "p2@example.com", UserRole.OVEROVATEL)
    other = login("p2@example.com")
    assert other.patch(url, json={"text": "Cudzí"}).status_code == 403
    assert other.delete(url).status_code == 403

    # An admin (with 2FA) may moderate any comment.
    admin_user = make_user(empty_factory, "a@example.com", UserRole.ADMIN, totp=True)
    admin = login("a@example.com", totp_code=pyotp.TOTP(admin_user.totp_secret).now())
    assert admin.delete(url).status_code == 200


def test_editor_cannot_comment(editor, promise_id):  # noqa: F811
    assert editor.post(comments_url(promise_id), json={"text": "Nie"}).status_code == 403


def test_comment_validation(verifier, promise_id):
    assert verifier.post(comments_url(promise_id), json={"text": ""}).status_code == 422
    assert verifier.post(comments_url(9999), json={"text": "Ahoj"}).status_code == 404
    assert verifier.patch(f"{comments_url(promise_id)}/9999", json={"text": "x"}).status_code == 404


@pytest.mark.parametrize("role", [UserRole.REDAKTOR, UserRole.OVEROVATEL])
def test_editor_and_verifier_manage_glossary(role, empty_factory):
    make_user(empty_factory, "u@example.com", role)
    user = login("u@example.com")

    term_id = user.post(f"{API}/glossary", json=TERM).json()["id"]
    assert user.patch(f"{API}/glossary/{term_id}", json={"short": "Nové"}).status_code == 200
    assert TestClient(app).get("/api/v1/glossary/koalicia").json()["short"] == "Nové"

    url = f"{API}/glossary/{term_id}"
    assert user.delete(url).status_code == 422  # no reason
    assert user.delete(url, params={"reason": "Duplicitný pojem"}).status_code == 204
    assert TestClient(app).get("/api/v1/glossary/koalicia").status_code == 404
    assert user.delete(url, params={"reason": "Ešte raz"}).status_code == 404

    entries = audit_entries(empty_factory, "glossary_term")
    assert [e.action for e in entries] == ["create", "update", "delete"]
    assert entries[-1].before["name"] == "Koalícia" and entries[-1].reason == "Duplicitný pojem"


def test_glossary_needs_login():
    assert TestClient(app).post(f"{API}/glossary", json=TERM).status_code == 401
