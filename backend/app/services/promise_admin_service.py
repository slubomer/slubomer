"""Editorial work on promises: add, fix, approve, reject, attach evidence.

Every change is written to the audit log in the same commit.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.text import normalize, slugify, unique_slug
from app.models import Category, Document, Evidence, Promise, Subject, User, Verdict
from app.models.enums import EvidenceRole, PromiseState, VerdictState
from app.schemas.admin import PromiseAdminDetail, PromiseAdminItem
from app.schemas.common import Page
from app.services import audit
from app.services.errors import Conflict, Invalid, NotFound, ReasonRequired

# Once filled in, these are the evidence of what was promised: no silent rewrites.
PROTECTED_FIELDS = ("quote", "page")
REQUIRED_FIELDS = ("subject", "title", "description")
# Where the promise comes from: needed before it can go public.
SOURCE_FIELDS = {"quote": "doslovná citácia", "page": "strana", "document": "dokument"}


# --- Reading ----------------------------------------------------------------


def search(
    db: Session,
    *,
    state: PromiseState | None = None,
    subject: str | None = None,
    category: str | None = None,
    without_category: bool = False,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page[PromiseAdminItem]:
    """All promises, including drafts and rejected ones. Oldest first (work queue)."""
    stmt = select(Promise)
    if state:
        stmt = stmt.where(Promise.state == state)
    if subject:
        stmt = stmt.where(Promise.subject.has(Subject.slug == subject))
    if category:
        stmt = stmt.where(Promise.category.has(Category.slug == category))
    if without_category:
        stmt = stmt.where(Promise.category_id.is_(None))
    if q and (needle := normalize(q)):
        stmt = stmt.where(Promise.search_text.contains(needle, autoescape=True))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Promise.subject), selectinload(Promise.category))
        .order_by(Promise.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[PromiseAdminItem.model_validate(p) for p in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _get(db: Session, promise_id: int) -> Promise:
    promise = db.get(Promise, promise_id)
    if promise is None:
        raise NotFound("Sľub sa nenašiel")
    return promise


def get_detail(db: Session, promise_id: int) -> PromiseAdminDetail:
    promise = db.scalar(
        select(Promise)
        .where(Promise.id == promise_id)
        .options(
            selectinload(Promise.subject),
            selectinload(Promise.category),
            selectinload(Promise.document),
            selectinload(Promise.evidence).selectinload(Evidence.document),
            selectinload(Promise.verdicts),
        )
        .execution_options(populate_existing=True)  # fresh data right after a change
    )
    if promise is None:
        raise NotFound("Sľub sa nenašiel")
    return PromiseAdminDetail.model_validate(promise)


# --- Lookups by slug / id ---------------------------------------------------


def _subject(db: Session, slug: str) -> Subject:
    subject = db.scalar(select(Subject).where(Subject.slug == slug))
    if subject is None:
        raise Invalid(f"Subjekt '{slug}' neexistuje")
    return subject


def _category(db: Session, slug: str | None) -> Category | None:
    if slug is None:
        return None
    category = db.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        raise Invalid(f"Kategória '{slug}' neexistuje")
    return category


def _document(db: Session, document_id: int | None) -> Document | None:
    if document_id is None:
        return None
    document = db.get(Document, document_id)
    if document is None:
        raise Invalid(f"Dokument {document_id} neexistuje")
    return document


def _resolve(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    """Turn slugs and ids from the request into model attributes."""
    resolved = dict(values)
    if "subject" in resolved:
        resolved["subject"] = _subject(db, resolved["subject"])
    if "category" in resolved:
        resolved["category"] = _category(db, resolved["category"])
    if "document_id" in resolved:
        resolved["document"] = _document(db, resolved.pop("document_id"))
    return resolved


# --- Changes ----------------------------------------------------------------


def create(db: Session, actor: User, values: dict[str, Any]) -> PromiseAdminDetail:
    """A promise added by hand starts as a draft, the public doesn't see it yet."""
    resolved = _resolve(db, values)
    subject = resolved["subject"]
    base = slugify(resolved["title"])
    taken = set(db.scalars(select(Promise.slug).where(Promise.slug.startswith(base))))

    promise = Promise(
        slug=unique_slug(base, subject.slug, taken), state=PromiseState.NAVRH, **resolved
    )
    promise.refresh_search_text()
    db.add(promise)
    db.flush()  # assigns promise.id for the audit entry
    audit.record(db, actor, "create", "promise", promise.id, after=audit.snapshot(promise))
    db.commit()
    return get_detail(db, promise.id)


def update(
    db: Session, actor: User, promise_id: int, values: dict[str, Any], reason: str | None
) -> PromiseAdminDetail:
    promise = _get(db, promise_id)

    for field in REQUIRED_FIELDS:
        if field in values and values[field] is None:
            raise Invalid(f"Pole '{field}' nemôže byť prázdne")
    for field in PROTECTED_FIELDS:
        old = getattr(promise, field)
        if field in values and old is not None and values[field] != old and not reason:
            raise ReasonRequired(f"Zmena poľa '{field}' potrebuje zdôvodnenie (reason)")

    resolved = _resolve(db, values)
    # The slug stays: it is in public links.
    audit.apply_changes(db, actor, promise, "promise", resolved, reason=reason)
    promise.refresh_search_text()
    db.commit()
    return get_detail(db, promise.id)


def _set_state(
    db: Session, actor: User, promise_id: int, state: PromiseState, reason: str | None = None
) -> PromiseAdminDetail:
    promise = _get(db, promise_id)
    if promise.state == state:
        raise Conflict(f"Sľub už je v stave '{state.value}'")
    action = "approve" if state == PromiseState.SCHVALENY else "reject"
    before = {"state": promise.state.value}
    promise.state = state
    after = {"state": state.value}
    audit.record(
        db, actor, action, "promise", promise.id, before=before, after=after, reason=reason
    )
    db.commit()
    return get_detail(db, promise.id)


def approve(db: Session, actor: User, promise_id: int) -> PromiseAdminDetail:
    """The promise appears on the public web. It must say where it comes from."""
    promise = _get(db, promise_id)
    missing = [label for field, label in SOURCE_FIELDS.items() if getattr(promise, field) is None]
    if missing:
        raise Invalid("Pred schválením doplň: " + ", ".join(missing))
    return _set_state(db, actor, promise_id, PromiseState.SCHVALENY)


def reject(db: Session, actor: User, promise_id: int, reason: str) -> PromiseAdminDetail:
    """Not a real promise (or a duplicate). Hidden from the public, kept for the record."""
    return _set_state(db, actor, promise_id, PromiseState.ZAMIETNUTY, reason)


# --- Evidence ---------------------------------------------------------------


def add_evidence(
    db: Session, actor: User, promise_id: int, values: dict[str, Any]
) -> PromiseAdminDetail:
    promise = _get(db, promise_id)
    resolved = _resolve(db, values)
    evidence = Evidence(promise=promise, **resolved)
    db.add(evidence)
    db.flush()
    audit.record(db, actor, "create", "evidence", evidence.id, after=audit.snapshot(evidence))
    db.commit()
    return get_detail(db, promise.id)


def _has_published_verdict(db: Session, promise_id: int) -> bool:
    published = select(Verdict.id).where(
        Verdict.promise_id == promise_id, Verdict.state == VerdictState.PUBLIKOVANY
    )
    return db.scalar(published.limit(1)) is not None


def delete_evidence(
    db: Session, actor: User, promise_id: int, evidence_id: int, reason: str
) -> PromiseAdminDetail:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None or evidence.promise_id != promise_id:
        raise NotFound("Dôkaz sa nenašiel")
    # A public verdict must keep the evidence it is based on.
    if evidence.role == EvidenceRole.PODKLAD and _has_published_verdict(db, promise_id):
        raise Conflict("Podklad publikovaného verdiktu sa nedá zmazať")
    # The whole row goes to the log, so the evidence can be restored if needed.
    before = audit.snapshot(evidence)
    audit.record(db, actor, "delete", "evidence", evidence.id, before=before, reason=reason)
    db.delete(evidence)
    db.commit()
    return get_detail(db, promise_id)
