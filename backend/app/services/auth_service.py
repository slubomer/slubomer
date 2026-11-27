"""Login, sessions and 2FA for the editorial team."""

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models import User, UserSession
from app.services import audit
from app.services.errors import ServiceError, TooManyAttempts, Unauthorized

# One message for every login failure, so it doesn't reveal which part was wrong.
INVALID_LOGIN = "Nesprávny e-mail alebo heslo"
TOTP_REQUIRED = "Zadaj kód z aplikácie na 2FA"
INVALID_TOTP = "Nesprávny 2FA kód"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _register_failure(db: Session, user: User) -> None:
    user.failed_logins += 1
    if user.failed_logins >= settings.max_failed_logins:
        user.locked_until = security.utcnow() + timedelta(minutes=settings.lockout_minutes)
        user.failed_logins = 0
    db.commit()


def authenticate(db: Session, email: str, password: str, totp_code: str | None) -> User:
    """Return the user if email, password and (when enabled) the 2FA code are right."""
    user = db.scalar(select(User).where(User.email == normalize_email(email)))

    if user and user.locked_until and security.as_utc(user.locked_until) > security.utcnow():
        raise TooManyAttempts("Príliš veľa neúspešných pokusov, skús to neskôr")

    if not security.verify_password(user.password_hash if user else None, password):
        if user:
            _register_failure(db, user)
        raise Unauthorized(INVALID_LOGIN)

    if not user.is_active:
        raise Unauthorized(INVALID_LOGIN)

    if user.totp_enabled:
        if not totp_code:
            raise Unauthorized(TOTP_REQUIRED)
        if not security.verify_totp(user.totp_secret or "", totp_code):
            _register_failure(db, user)
            raise Unauthorized(INVALID_TOTP)

    # Successful login: reset the counter, upgrade the hash if parameters changed.
    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = security.utcnow()
    if security.password_needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)
    db.commit()
    return user


def create_session(db: Session, user: User) -> str:
    """Store a new session and return the token for the cookie."""
    token = security.new_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=security.hash_token(token),
            expires_at=security.utcnow() + timedelta(hours=settings.session_ttl_hours),
        )
    )
    # Drop this user's expired sessions while we're here.
    db.execute(
        delete(UserSession).where(
            UserSession.user_id == user.id, UserSession.expires_at < security.utcnow()
        )
    )
    db.commit()
    return token


def user_from_token(db: Session, token: str | None) -> User | None:
    """The active user behind a session cookie, or None."""
    if not token:
        return None
    session = db.scalar(
        select(UserSession).where(UserSession.token_hash == security.hash_token(token))
    )
    if session is None or security.as_utc(session.expires_at) <= security.utcnow():
        return None
    return session.user if session.user.is_active else None


def end_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == security.hash_token(token)))
        db.commit()


def end_all_sessions(db: Session, user: User) -> None:
    """Log the user out everywhere (deactivation, password change)."""
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()


def start_totp_setup(db: Session, user: User) -> tuple[str, str]:
    """Generate a new 2FA secret. It is enabled only after confirm_totp()."""
    if user.totp_enabled:
        raise ServiceError("2FA je už zapnutá")
    user.totp_secret = security.new_totp_secret()
    db.commit()
    return user.totp_secret, security.totp_uri(user.totp_secret, user.email)


def confirm_totp(db: Session, user: User, code: str) -> None:
    if user.totp_enabled:
        raise ServiceError("2FA je už zapnutá")
    if not user.totp_secret:
        raise ServiceError("Najprv spusti nastavenie 2FA")
    if not security.verify_totp(user.totp_secret, code):
        raise ServiceError(INVALID_TOTP)
    user.totp_enabled = True
    audit.record(db, user, "enable_2fa", "app_user", user.id, after={"totp_enabled": True})
    db.commit()


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not security.verify_password(user.password_hash, current):
        raise Unauthorized("Súčasné heslo nie je správne")
    user.password_hash = security.hash_password(new)
    audit.record(db, user, "change_password", "app_user", user.id, after={"password_changed": True})
    end_all_sessions(db, user)  # also commits
