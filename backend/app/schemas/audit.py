"""Audit log responses."""

from datetime import datetime
from typing import Any

from app.schemas.common import ApiModel


class ActorOut(ApiModel):
    id: int
    name: str


class AuditEntryOut(ApiModel):
    id: int
    actor: ActorOut | None  # None = the system (import, CLI)
    action: str
    entity: str
    entity_id: int | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    created_at: datetime
