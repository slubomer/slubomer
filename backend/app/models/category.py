"""Topic of a promise (healthcare, education, ...)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    label: Mapped[str] = mapped_column(String(100))
    tagline: Mapped[str | None] = mapped_column(String(200))
