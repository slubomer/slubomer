"""A quoted passage from a document that supports a promise or its verdict."""

from sqlalchemy import ForeignKey, Text
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
    quote: Mapped[str] = mapped_column(Text)
    ai_generated: Mapped[bool] = mapped_column(default=False)

    promise: Mapped["Promise"] = relationship(back_populates="evidence")  # noqa: F821
    document: Mapped[Document] = relationship()
