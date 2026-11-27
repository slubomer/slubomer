"""A piece of evidence for a promise or its verdict.

Usually a quoted passage from a document. A vote in the National Council has
no quote, its numbers are in `vote` instead.
"""

from typing import Any

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.document import Document
from app.models.enums import EvidenceRole, db_enum


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    promise_id: Mapped[int] = mapped_column(ForeignKey("promise.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"))
    role: Mapped[EvidenceRole] = mapped_column(db_enum(EvidenceRole))
    page: Mapped[int | None]
    quote: Mapped[str | None] = mapped_column(Text)  # empty for votes and imported web links
    # Vote result, e.g. {"faza": "finalne", "vysledok": "Návrh prešiel", "strana_za": 39, ...}
    vote: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ai_generated: Mapped[bool] = mapped_column(default=False)

    promise: Mapped["Promise"] = relationship(back_populates="evidence")  # noqa: F821
    document: Mapped[Document] = relationship()
