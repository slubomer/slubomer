"""Published document: a party programme or a source for a verdict."""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import DocumentKind, db_enum


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[DocumentKind] = mapped_column(db_enum(DocumentKind))
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(String(1000))
    # Archived copy and its hash are filled in by document upload (B-10).
    archived_path: Mapped[str | None] = mapped_column(String(500))
    sha256: Mapped[str | None] = mapped_column(String(64), unique=True)
    published_at: Mapped[date | None] = mapped_column(Date)
