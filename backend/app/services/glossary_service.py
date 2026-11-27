"""Glossary of political terms."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import sk_sort_key, slugify
from app.models import GlossaryTerm, User
from app.services import audit
from app.services.errors import Conflict, Invalid, NotFound

# Fields a term must always have.
REQUIRED_FIELDS = ("name", "short", "example")


def list_terms(db: Session) -> list[GlossaryTerm]:
    terms = db.scalars(select(GlossaryTerm)).all()
    # Sorted in Python: database collations differ, the glossary is small.
    return sorted(terms, key=lambda t: sk_sort_key(t.name))


def get_term(db: Session, slug: str) -> GlossaryTerm | None:
    return db.scalar(select(GlossaryTerm).where(GlossaryTerm.slug == slug))


def create_term(db: Session, actor: User, values: dict[str, Any]) -> GlossaryTerm:
    slug = slugify(values["name"], max_length=100)
    if get_term(db, slug):
        raise Conflict(f"Pojem '{slug}' už v slovníku je")
    term = GlossaryTerm(slug=slug, **values)
    db.add(term)
    db.flush()
    audit.record(db, actor, "create", "glossary_term", term.id, after=audit.snapshot(term))
    db.commit()
    return term


def _get(db: Session, term_id: int) -> GlossaryTerm:
    term = db.get(GlossaryTerm, term_id)
    if term is None:
        raise NotFound("Pojem sa nenašiel")
    return term


def update_term(db: Session, actor: User, term_id: int, values: dict[str, Any]) -> GlossaryTerm:
    """The slug stays, so links to the term keep working after a rename."""
    term = _get(db, term_id)
    for field in (*REQUIRED_FIELDS, "stems"):
        if field in values and values[field] is None:
            raise Invalid(f"Pole '{field}' nemôže byť prázdne")
    audit.apply_changes(db, actor, term, "glossary_term", values)
    db.commit()
    return term


def delete_term(db: Session, actor: User, term_id: int, reason: str) -> None:
    term = _get(db, term_id)
    # The whole row goes to the log, so the term can be restored if needed.
    before = audit.snapshot(term)
    audit.record(db, actor, "delete", "glossary_term", term.id, before=before, reason=reason)
    db.delete(term)
    db.commit()
