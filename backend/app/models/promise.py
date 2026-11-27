"""Election promise, quoted word for word from a programme."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.text import normalize
from app.models.category import Category
from app.models.document import Document
from app.models.enums import PromiseState, PromiseType, db_enum
from app.models.subject import Subject


class Promise(Base):
    __tablename__ = "promise"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"), index=True)
    # Category and type are filled in later by an editor or AI, so they may be empty.
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))

    title: Mapped[str] = mapped_column(String(300))  # short, readable name
    description: Mapped[str] = mapped_column(Text)  # what was promised, in full
    quote: Mapped[str | None] = mapped_column(Text)  # verbatim text from the programme, if known
    page: Mapped[int | None]  # page of the quote in the document
    type: Mapped[PromiseType | None] = mapped_column(db_enum(PromiseType), index=True)
    state: Mapped[PromiseState] = mapped_column(
        db_enum(PromiseState), default=PromiseState.NAVRH, index=True
    )
    ai_generated: Mapped[bool] = mapped_column(default=False)  # AI Act labelling

    # Lowercase text without diacritics, so "skola" finds "školstvo".
    search_text: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subject: Mapped[Subject] = relationship()
    category: Mapped[Category | None] = relationship()
    document: Mapped[Document | None] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        back_populates="promise", order_by="Evidence.id"
    )
    verdicts: Mapped[list["Verdict"]] = relationship(  # noqa: F821
        back_populates="promise", order_by="Verdict.version.desc()"
    )
    comments: Mapped[list["PromiseComment"]] = relationship(  # noqa: F821
        back_populates="promise", order_by="PromiseComment.id"
    )

    def refresh_search_text(self) -> None:
        """Call after changing the title, text, category or subject."""
        category = self.category.label if self.category else ""
        parts = (self.title, self.description, category, self.subject.name)
        self.search_text = normalize(" ".join(parts))
