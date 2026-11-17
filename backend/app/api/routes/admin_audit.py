"""Audit log for the editorial team: who changed what, when and why."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_role
from app.core.db import DbSession
from app.models import User
from app.models.enums import UserRole
from app.schemas.audit import AuditEntryOut
from app.schemas.common import Page
from app.services import audit

router = APIRouter(prefix="/admin/audit", tags=["admin: audit"])

EditorialUser = Annotated[User, Depends(require_role(UserRole.REDAKTOR, UserRole.OVEROVATEL))]


@router.get("")
def list_audit(
    user: EditorialUser,
    db: DbSession,
    entity: Annotated[str | None, Query(description="Napr. promise, verdict, app_user")] = None,
    entity_id: int | None = None,
    actor_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[AuditEntryOut]:
    """Newest first. Filter by entity (and its id) or by the person who made the change."""
    return audit.search(
        db, entity=entity, entity_id=entity_id, actor_id=actor_id, page=page, page_size=page_size
    )
