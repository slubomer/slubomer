"""One version of a promise's verdict. Versions are never overwritten."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import VerdictState, VerdictValue, db_enum


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
