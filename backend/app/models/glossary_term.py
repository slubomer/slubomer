"""Political term explained in plain language (glossary)."""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GlossaryTerm(Base):
    __tablename__ = "glossary_term"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    short: Mapped[str] = mapped_column(String(300))
    long: Mapped[str | None] = mapped_column(Text)
    example: Mapped[str] = mapped_column(String(300))
    wiki_url: Mapped[str | None] = mapped_column(String(500))
    # Regex word starts that match inflected forms, used by the frontend to highlight terms.
    stems: Mapped[list[str]] = mapped_column(JSON, default=list)
