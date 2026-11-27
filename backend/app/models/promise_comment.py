"""A political scientist's comment that explains a promise or its verdict.

A promise may have many comments. They are separate from verdicts, so they can
be added to a verdict that is already published (and locked), including one
that AI approved on its own.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PromiseComment(Base):
    __tablename__ = "promise_comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    promise_id: Mapped[int] = mapped_column(ForeignKey("promise.id"), index=True)
    # Kept internal: only the author may edit their comment.
    author_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"))
    # Role only (e.g. "politológ"), no names on the public web (GDPR).
    author_role: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    promise: Mapped["Promise"] = relationship(back_populates="comments")  # noqa: F821
