"""Glossary of political terms."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import sk_sort_key
from app.models import GlossaryTerm


def list_terms(db: Session) -> list[GlossaryTerm]:
    terms = db.scalars(select(GlossaryTerm)).all()
    # Sorted in Python: database collations differ, the glossary is small.
    return sorted(terms, key=lambda t: sk_sort_key(t.name))


def get_term(db: Session, slug: str) -> GlossaryTerm | None:
    return db.scalar(select(GlossaryTerm).where(GlossaryTerm.slug == slug))
