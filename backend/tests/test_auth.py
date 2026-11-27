"""Login, sessions, 2FA and roles."""

import pyotp
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models import User
from app.models.enums import UserRole
from app.services import user_service

PASSWORD = "spravne-heslo-123"


def make_user(factory, email: str, role: UserRole, *, totp: bool = False) -> User:
    with factory() as db:
        user = user_service.create_user(db, email, email.split("@")[0], role, PASSWORD)
        if totp:
            user.totp_secret = pyotp.random_base32()
            user.totp_enabled = True
            db.commit()
        return user


def login(email: str, password: str = PASSWORD, totp_code: str | None = None) -> TestClient:
    """A new browser (own cookie jar) that logs in."""
    browser = TestClient(app)
    response = browser.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "totp_code": totp_code},
    )
    browser.last_status = response.status_code
    browser.last_body = response.json() if response.content else None
    return browser


def test_login_sets_httponly_cookie_and_me_works(empty_factory):
    make_user(empty_factory, "redaktor@example.com", UserRole.REDAKTOR)

    browser = login("Redaktor@Example.com ")  # email is case-insensitive

    assert browser.last_status == 200
    cookie = browser.cookies.get(settings.session_cookie_name)
    assert cookie
    me = browser.get("/api/v1/auth/me").json()
    assert me["email"] == "redaktor@example.com" and me["role"] == "redaktor"
    assert "password_hash" not in me


def test_password_is_stored_hashed(empty_factory):
    user = make_user(empty_factory, "a@example.com", UserRole.REDAKTOR)

    assert user.password_hash.startswith("$argon2")
    assert PASSWORD not in user.password_hash


def test_wrong_password_and_unknown_email_look_the_same(empty_factory):
    make_user(empty_factory, "a@example.com", UserRole.REDAKTOR)

    wrong = login("a@example.com", "zle-heslo-123456")
    unknown = login("nikto@example.com")

    assert wrong.last_status == unknown.last_status == 401
    assert wrong.last_body == unknown.last_body


def test_account_is_locked_after_repeated_failures(empty_factory):
    make_user(empty_factory, "a@example.com", UserRole.REDAKTOR)

    for _ in range(settings.max_failed_logins):
        assert login("a@example.com", "zle-heslo-123456").last_status == 401

    # Even the right password is refused while locked.
    assert login("a@example.com").last_status == 429


def test_not_logged_in_and_logout(empty_factory):
    make_user(empty_factory, "a@example.com", UserRole.REDAKTOR)
    assert TestClient(app).get("/api/v1/auth/me").status_code == 401

    browser = login("a@example.com")
    assert browser.post("/api/v1/auth/logout").status_code == 204
    # The old token is deleted on the server, not only in the browser.
    assert browser.get("/api/v1/auth/me").status_code == 401


def test_totp_setup_and_login_with_code(empty_factory):
    make_user(empty_factory, "a@example.com", UserRole.OVEROVATEL)
    browser = login("a@example.com")

    setup = browser.post("/api/v1/auth/2fa/setup").json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    totp = pyotp.TOTP(setup["secret"])
    assert browser.post("/api/v1/auth/2fa/confirm", json={"code": "000000"}).status_code == 400
    assert browser.post("/api/v1/auth/2fa/confirm", json={"code": totp.now()}).status_code == 204

    without_code = login("a@example.com")
    assert without_code.last_status == 401
    assert "2FA" in without_code.last_body["detail"]
    assert login("a@example.com", totp_code="123456").last_status == 401
    assert login("a@example.com", totp_code=totp.now()).last_status == 200


@pytest.mark.parametrize("role", [UserRole.REDAKTOR, UserRole.OVEROVATEL])
def test_non_admins_cannot_manage_users(empty_factory, role):
    make_user(empty_factory, "a@example.com", role)

    assert login("a@example.com").get("/api/v1/admin/users").status_code == 403


def test_admin_needs_2fa(empty_factory):
    make_user(empty_factory, "admin@example.com", UserRole.ADMIN)

    response = login("admin@example.com").get("/api/v1/admin/users")

    assert response.status_code == 403
    assert "2FA" in response.json()["detail"]


def test_admin_manages_users(empty_factory):
    admin = make_user(empty_factory, "admin@example.com", UserRole.ADMIN, totp=True)
    browser = login("admin@example.com", totp_code=pyotp.TOTP(admin.totp_secret).now())

    new = {"email": "nova@example.com", "name": "Nová", "role": "redaktor", "password": PASSWORD}
    created = browser.post("/api/v1/admin/users", json=new)
    assert created.status_code == 201
    assert browser.post("/api/v1/admin/users", json=new).status_code == 409
    short = {**new, "email": "x@example.com", "password": "kratke"}
    assert browser.post("/api/v1/admin/users", json=short).status_code == 422

    # Deactivation logs the user out everywhere.
    editor = login("nova@example.com")
    assert editor.get("/api/v1/auth/me").status_code == 200
    user_id = created.json()["id"]
    assert (
        browser.patch(f"/api/v1/admin/users/{user_id}", json={"is_active": False}).status_code
        == 200
    )
    assert editor.get("/api/v1/auth/me").status_code == 401
    assert login("nova@example.com").last_status == 401

    # An admin can't deactivate themselves.
    assert (
        browser.patch(f"/api/v1/admin/users/{admin.id}", json={"is_active": False}).status_code
        == 403
    )
    assert [u["email"] for u in browser.get("/api/v1/admin/users").json()] == [
        "admin@example.com",
        "nova@example.com",
    ]


def test_password_change_logs_out_other_sessions(empty_factory):
    make_user(empty_factory, "a@example.com", UserRole.REDAKTOR)
    laptop, phone = login("a@example.com"), login("a@example.com")

    body = {"current_password": PASSWORD, "new_password": "uplne-nove-heslo-456"}
    assert laptop.post("/api/v1/auth/password", json=body).status_code == 200

    assert laptop.get("/api/v1/auth/me").status_code == 200  # got a fresh cookie
    assert phone.get("/api/v1/auth/me").status_code == 401
    assert login("a@example.com").last_status == 401
    assert login("a@example.com", "uplne-nove-heslo-456").last_status == 200
