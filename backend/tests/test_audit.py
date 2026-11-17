"""Audit log entries and the published-verdict guard."""

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.import_promises import import_promises
from app.main import app
from app.models import AuditLog, Promise, Subject, Verdict
from app.models.enums import PromiseState, UserRole, VerdictState, VerdictValue
from app.models.verdict import VerdictLocked
from tests.test_auth import PASSWORD, login, make_user


def admin_browser(factory) -> tuple[TestClient, int]:
    admin = make_user(factory, "admin@example.com", UserRole.ADMIN, totp=True)
    return login("admin@example.com", totp_code=pyotp.TOTP(admin.totp_secret).now()), admin.id


def entries(factory) -> list[AuditLog]:
    with factory() as db:
        return list(db.scalars(select(AuditLog).order_by(AuditLog.id)))


def test_user_changes_are_logged_without_secrets(empty_factory):
    browser, admin_id = admin_browser(empty_factory)
    new = {"email": "r@example.com", "name": "Redaktor", "role": "redaktor", "password": PASSWORD}
    user_id = browser.post("/api/v1/admin/users", json=new).json()["id"]
    browser.patch(f"/api/v1/admin/users/{user_id}", json={"role": "overovatel"})
    browser.patch(f"/api/v1/admin/users/{user_id}", json={"password": "nove-heslo-na-reset"})

    created, role_change, reset = entries(empty_factory)[-3:]

    assert (created.action, created.actor_id, created.entity_id) == ("create", admin_id, user_id)
    assert created.after["email"] == "r@example.com"
    assert "password_hash" not in created.after and "totp_secret" not in created.after
    # Only what changed is stored.
    assert role_change.before == {"role": "redaktor"} and role_change.after == {
        "role": "overovatel"
    }
    assert reset.after["password_reset"] is True
    assert "password_hash" not in reset.after


def test_password_change_and_2fa_are_logged(empty_factory):
    user = make_user(empty_factory, "a@example.com", UserRole.REDAKTOR)
    browser = login("a@example.com")
    secret = browser.post("/api/v1/auth/2fa/setup").json()["secret"]
    browser.post("/api/v1/auth/2fa/confirm", json={"code": pyotp.TOTP(secret).now()})
    browser.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": "uplne-nove-heslo-456"},
    )

    actions = [(e.action, e.actor_id) for e in entries(empty_factory) if e.entity_id == user.id]

    assert actions == [("create", None), ("enable_2fa", user.id), ("change_password", user.id)]


def test_import_writes_one_summary_entry(empty_factory):
    records = [
        {"strana": "Strana", "nazov": f"Sľub {i}", "telo": f"Text {i}", "datum": None, "stav": ""}
        for i in range(3)
    ]
    with empty_factory() as db:
        import_promises(db, records, source="sluby.json")
        import_promises(db, records, source="sluby.json")  # nothing new -> no entry

    (entry,) = entries(empty_factory)
    assert (entry.action, entry.entity, entry.actor_id) == ("import", "promise", None)
    assert entry.after == {"created": 3, "categorized": 0, "skipped": 0, "source": "sluby.json"}


def test_audit_api_for_editorial_team_only(empty_factory):
    browser, _ = admin_browser(empty_factory)
    new = {"email": "r@example.com", "name": "Redaktor", "role": "redaktor", "password": PASSWORD}
    user_id = browser.post("/api/v1/admin/users", json=new).json()["id"]

    editor = login("r@example.com")
    page = editor.get("/api/v1/admin/audit", params={"entity": "app_user", "entity_id": user_id})

    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 1
    assert body["items"][0]["actor"]["name"] == "admin"
    assert TestClient(app).get("/api/v1/admin/audit").status_code == 401


def published_verdict(factory) -> int:
    with factory() as db:
        subject = Subject(slug="s", name="Strana")
        promise = Promise(
            slug="p",
            subject=subject,
            title="Sľub",
            description="Text",
            state=PromiseState.SCHVALENY,
        )
        verdict = Verdict(
            promise=promise,
            version=1,
            value=VerdictValue.V_PROCESE,
            explanation="Pracuje sa na tom.",
            state=VerdictState.PUBLIKOVANY,
        )
        db.add(verdict)
        db.commit()
        return verdict.id


def test_published_verdict_cannot_be_changed_or_deleted(empty_factory):
    verdict_id = published_verdict(empty_factory)

    with empty_factory() as db:
        verdict = db.get(Verdict, verdict_id)
        verdict.explanation = "Prepísané potichu."
        with pytest.raises(VerdictLocked):
            db.commit()

    with empty_factory() as db:
        db.delete(db.get(Verdict, verdict_id))
        with pytest.raises(VerdictLocked):
            db.commit()


def test_published_verdict_can_only_be_superseded(empty_factory):
    verdict_id = published_verdict(empty_factory)

    with empty_factory() as db:
        db.get(Verdict, verdict_id).state = VerdictState.NAHRADENY
        db.commit()  # allowed: a newer version replaces it

    with empty_factory() as db:
        db.get(Verdict, verdict_id).state = VerdictState.PUBLIKOVANY
        with pytest.raises(VerdictLocked):
            db.commit()  # history can't be brought back to life


def test_draft_verdict_can_be_edited(empty_factory):
    verdict_id = published_verdict(empty_factory)
    with empty_factory() as db:
        draft = Verdict(
            promise_id=db.get(Verdict, verdict_id).promise_id,
            version=2,
            value=VerdictValue.SPLNENY,
            explanation="Návrh",
            state=VerdictState.NAVRH,
        )
        db.add(draft)
        db.commit()
        draft.explanation = "Upravený návrh"
        db.commit()  # drafts are not locked
