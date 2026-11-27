"""Audit log: every service that changes data calls record().

record() only adds the row to the session. The caller's commit saves it
together with the change, so a change never exists without its audit entry.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.schemas.audit import AuditEntryOut
from app.schemas.common import Page

# Never copied into the audit log.
SECRET_FIELDS = {"password_hash", "totp_secret", "search_text"}


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def snapshot(obj: Any) -> dict[str, Any]:
    """Column values of a model row as plain JSON, without secrets."""
    return {
        attr.key: _json_value(getattr(obj, attr.key))
        for attr in inspect(obj).mapper.column_attrs
        if attr.key not in SECRET_FIELDS
    }


def changes(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict, dict]:
    """Keep only the fields that changed, so the log stays readable."""
    changed = {k for k in after if before.get(k) != after.get(k)}
    return {k: before.get(k) for k in changed}, {k: after[k] for k in changed}


def record(
    db: Session,
    actor: User | None,
    action: str,
    entity: str,
    entity_id: int | None,
    *,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before=before,
            after=after,
            reason=reason,
        )
    )


def apply_changes(
    db: Session,
    actor: User | None,
    obj: Any,
    entity: str,
    values: dict[str, Any],
    *,
    reason: str | None = None,
) -> bool:
    """Set the given attributes on a row and log what really changed.

    Returns False when nothing changed (then nothing is logged).
    """
    before = snapshot(obj)
    for key, value in values.items():
        setattr(obj, key, value)
    db.flush()  # a changed relationship (e.g. category) fills its *_id column only on flush
    old_values, new_values = changes(before, snapshot(obj))
    if not new_values:
        return False
    record(db, actor, "update", entity, obj.id, before=old_values, after=new_values, reason=reason)
    return True


def search(
    db: Session,
    *,
    entity: str | None = None,
    entity_id: int | None = None,
    actor_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page[AuditEntryOut]:
    """Newest first, optionally only for one entity or one person."""
    stmt = select(AuditLog)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[AuditEntryOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
