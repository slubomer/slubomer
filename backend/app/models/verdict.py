"""One version of a promise's verdict. Versions are never overwritten."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, event, func, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import VerdictState, VerdictValue, db_enum
from app.services.errors import Conflict


class Verdict(Base):
    __tablename__ = "verdict"
    __table_args__ = (UniqueConstraint("promise_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    promise_id: Mapped[int] = mapped_column(ForeignKey("promise.id"), index=True)
    version: Mapped[int]
    value: Mapped[VerdictValue] = mapped_column(db_enum(VerdictValue))
    explanation: Mapped[str] = mapped_column(Text)  # plain-language reason
    state: Mapped[VerdictState] = mapped_column(db_enum(VerdictState), index=True)
    confidence: Mapped[float | None]  # AI confidence 0–1
    ai_generated: Mapped[bool] = mapped_column(default=False)
    # Role only (e.g. "politológ"), no names on the public web (GDPR).
    reviewer_role: Mapped[str | None] = mapped_column(String(50))
    review_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    promise: Mapped["Promise"] = relationship(back_populates="verdicts")  # noqa: F821


class VerdictLocked(Conflict):
    """Attempt to change a verdict that was already published (HTTP 409)."""


# Once published, a verdict version is history: the only allowed change is
# publikovany -> nahradeny when a newer version replaces it. New content means
# a new Verdict row with a higher version.
# In PostgreSQL a trigger enforces the same rule for raw SQL and bulk updates
# (migration 0005). This ORM check gives a clear error and covers SQLite in tests.
_FROZEN_STATES = {VerdictState.PUBLIKOVANY, VerdictState.NAHRADENY}


@event.listens_for(Verdict, "before_update")
def _guard_published_verdict(mapper, connection, target: Verdict) -> None:
    state = inspect(target)
    old_state = state.attrs.state.history.deleted
    was = old_state[0] if old_state else target.state
    if was not in _FROZEN_STATES:
        return  # drafts and returned versions may still be edited

    changed = {a.key for a in state.attrs if a.history.has_changes()}
    allowed = (
        changed == {"state"}
        and was == VerdictState.PUBLIKOVANY
        and target.state == VerdictState.NAHRADENY
    )
    if changed and not allowed:
        raise VerdictLocked(
            "Publikovaný verdikt sa nedá zmeniť, vytvor novú verziu (zmenené: "
            + ", ".join(sorted(changed))
            + ")"
        )


@event.listens_for(Verdict, "before_delete")
def _guard_verdict_delete(mapper, connection, target: Verdict) -> None:
    if target.state in _FROZEN_STATES:
        raise VerdictLocked("Publikovaný verdikt sa nedá zmazať")
