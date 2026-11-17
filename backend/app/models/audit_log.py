"""Who changed what, when and why. Rows are only ever added, never changed.

In PostgreSQL a trigger (migration 0005) rejects UPDATE and DELETE on this table.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_entity", "entity", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # None = done by the system (import, CLI), not by a logged-in person.
    # Users are deactivated, never deleted: the database refuses to delete
    # a user who appears in the log, so every entry keeps its author.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), index=True)
    action: Mapped[str] = mapped_column(String(50))  # e.g. "create", "update", "import"
    entity: Mapped[str] = mapped_column(String(50))  # table name, e.g. "promise"
    entity_id: Mapped[int | None]  # None for bulk actions like an import
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    actor: Mapped[User | None] = relationship()
