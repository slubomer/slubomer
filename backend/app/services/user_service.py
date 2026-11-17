"""User management for admins."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.text import sk_sort_key
from app.models import User
from app.models.enums import UserRole
from app.services import audit, auth_service
from app.services.errors import Conflict, Forbidden, NotFound


def list_users(db: Session) -> list[User]:
    # Sorted in Python: Slovak alphabet, case-insensitive (the team is small).
    return sorted(db.scalars(select(User)), key=lambda u: sk_sort_key(u.name))


def create_user(
    db: Session,
    email: str,
    name: str,
    role: UserRole,
    password: str,
    *,
    actor: User | None = None,
) -> User:
    """actor = the admin creating the account, None when created from the CLI."""
    email = auth_service.normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise Conflict("Používateľ s týmto e-mailom už existuje")
    user = User(
        email=email, name=name.strip(), role=role, password_hash=security.hash_password(password)
    )
    db.add(user)
    db.flush()  # assigns user.id for the audit entry
    audit.record(db, actor, "create", "app_user", user.id, after=audit.snapshot(user))
    db.commit()
    return user


def update_user(
    db: Session,
    acting: User,
    user_id: int,
    *,
    name: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    password: str | None = None,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("Používateľ sa nenašiel")

    # An admin can't lock themselves out by mistake.
    if user.id == acting.id and (is_active is False or (role and role != UserRole.ADMIN)):
        raise Forbidden("Vlastný účet si nemôžeš deaktivovať ani odobrať rolu admina")

    before = audit.snapshot(user)
    if name is not None:
        user.name = name.strip()
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    if password is not None:
        user.password_hash = security.hash_password(password)
        user.failed_logins = 0
        user.locked_until = None

    old_values, new_values = audit.changes(before, audit.snapshot(user))
    if password is not None:
        new_values["password_reset"] = True  # the hash itself never goes to the log
    if new_values:
        audit.record(db, acting, "update", "app_user", user.id, before=old_values, after=new_values)
    db.commit()

    # A deactivated user or a reset password ends all existing logins.
    if is_active is False or password is not None:
        auth_service.end_all_sessions(db, user)
    return user
