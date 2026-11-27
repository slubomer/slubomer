"""Passwords, session tokens and 2FA codes. No database access here."""

import hashlib
import secrets
from datetime import UTC, datetime

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()

# Hash of a random password: lets a login with an unknown email take as long
# as one with a wrong password, so attackers can't tell which emails exist.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

TOTP_ISSUER = "Sľubomer"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Check a password. password_hash=None (unknown user) still costs one hash check."""
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    return password_hash is not None


def password_needs_rehash(password_hash: str) -> bool:
    """True when the hash uses older argon2 parameters than the current ones."""
    return _hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    """Random token for the cookie. Only its hash goes to the database."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    """otpauth:// link for authenticator apps (shown as a QR code by the frontend)."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    # valid_window=1 accepts the previous and next 30 s code (clock drift).
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """SQLite returns datetimes without a time zone; treat them as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)
