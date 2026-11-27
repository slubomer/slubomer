"""Login, logout and the current user's own account (2FA, password)."""

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, session_token
from app.core.config import settings
from app.core.db import DbSession
from app.models import User
from app.schemas.user import (
    LoginRequest,
    PasswordChangeRequest,
    TotpConfirmRequest,
    TotpSetupOut,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, db: DbSession, user: User) -> None:
    token = auth_service.create_session(db, user)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,  # JavaScript can't read it, so XSS can't steal the session
        secure=settings.cookie_secure,
        samesite="lax",  # not sent with cross-site POSTs (CSRF protection)
        path="/",
    )


@router.post("/login")
def login(body: LoginRequest, response: Response, db: DbSession) -> UserOut:
    """Log in with email and password (+ 2FA code if enabled). Sets the session cookie."""
    user = auth_service.authenticate(db, body.email, body.password, body.totp_code)
    _set_session_cookie(response, db, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> None:
    auth_service.end_session(db, session_token(request))
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    """The logged-in user."""
    return user


@router.post("/2fa/setup")
def totp_setup(user: CurrentUser, db: DbSession) -> TotpSetupOut:
    """Step 1: get a secret for the authenticator app (QR code from otpauth_uri)."""
    secret, uri = auth_service.start_totp_setup(db, user)
    return TotpSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/2fa/confirm", status_code=status.HTTP_204_NO_CONTENT)
def totp_confirm(body: TotpConfirmRequest, user: CurrentUser, db: DbSession) -> None:
    """Step 2: confirm with the first code from the app. From now on login needs it."""
    auth_service.confirm_totp(db, user, body.code)


@router.post("/password")
def change_password(
    body: PasswordChangeRequest, response: Response, user: CurrentUser, db: DbSession
) -> UserOut:
    """Change your password. Logs out all other sessions, this one gets a new cookie."""
    auth_service.change_password(db, user, body.current_password, body.new_password)
    _set_session_cookie(response, db, user)
    return user
