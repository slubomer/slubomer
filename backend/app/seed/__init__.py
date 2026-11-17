"""Load sample data from the prototype. Safe to run repeatedly: existing rows are kept.

Usage (in backend/): python -m app.seed
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import normalize
from app.models import Category, Document, Evidence, GlossaryTerm, Promise, Subject, Verdict
from app.models.enums import (
    DocumentKind,
    EvidenceRole,
    PromiseState,
    PromiseType,
    VerdictState,
    VerdictValue,
)
from app.seed import data

# Newest verdict is published on this day, each next promise one day earlier.
_LATEST_PUBLISHED = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def slugify(text: str) -> str:
    return "-".join(normalize(text).split())


def _get_or_create[T](db: Session, model: type[T], lookup: dict, values: dict) -> T:
    """Return the row matching `lookup`, or add a new one built from lookup + values."""
    row = db.scalar(select(model).filter_by(**lookup))
    if row is None:
        row = model(**lookup, **values)
        db.add(row)
        db.flush()
    return row


def _by_slug[T](db: Session, model: type[T], rows: list[dict]) -> dict[str, T]:
    """Get or create each row by its slug, return them keyed by slug."""
    return {
        r["slug"]: _get_or_create(
            db, model, {"slug": r["slug"]}, {k: v for k, v in r.items() if k != "slug"}
        )
        for r in rows
    }


def seed(db: Session) -> None:
    subjects = _by_slug(db, Subject, data.SUBJECTS)
    categories = _by_slug(db, Category, data.CATEGORIES)

    # One sample programme per subject; promises quote it.
    programmes = {
        slug: _get_or_create(
            db,
            Document,
            {"title": f"Volebný program – {subject.name} (ukážka)"},
            {"kind": DocumentKind.PROGRAM, "published_at": date(2023, 8, 1)},
        )
        for slug, subject in subjects.items()
    }
    evidence_docs = {
        ptype: _get_or_create(
            db, Document, {"title": d["title"]}, {"kind": DocumentKind(d["kind"])}
        )
        for ptype, d in data.EVIDENCE_DOCUMENTS.items()
    }

    for i, p in enumerate(data.PROMISES):
        if db.scalar(select(Promise).where(Promise.slug == p["slug"])):
            continue  # already seeded
        subject = subjects[p["subject"]]
        category = categories[p["category"]]
        page = 3 + i  # sample page numbers

        promise = Promise(
            slug=p["slug"],
            title=p["title"],
            quote=p["quote"],
            page=page,
            type=PromiseType(p["type"]),
            state=PromiseState.SCHVALENY,
            ai_generated=True,  # in the real pipeline AI extracts promises
            subject=subject,
            category=category,
            document=programmes[p["subject"]],
            search_text=normalize(f"{p['title']} {p['quote']} {category.label} {subject.name}"),
        )
        db.add(promise)

        value, explanation = p["verdict"]
        db.add_all(
            [
                Evidence(
                    promise=promise,
                    document=programmes[p["subject"]],
                    role=EvidenceRole.ZDROJ,
                    page=page,
                    quote=p["quote"],
                    ai_generated=True,
                ),
                Evidence(
                    promise=promise,
                    document=evidence_docs[p["type"]],
                    role=EvidenceRole.PODKLAD,
                    page=4,
                    quote=f"Ukážkový úryvok z dokumentu: {explanation}",
                    ai_generated=True,
                ),
            ]
        )

        published_at = _LATEST_PUBLISHED - timedelta(days=i)
        versions = [*p.get("history", []), (value, explanation)]
        for version, (v_value, v_text) in enumerate(versions, start=1):
            is_current = version == len(versions)
            db.add(
                Verdict(
                    promise=promise,
                    version=version,
                    value=VerdictValue(v_value),
                    explanation=v_text,
                    state=VerdictState.PUBLIKOVANY if is_current else VerdictState.NAHRADENY,
                    ai_generated=True,
                    reviewer_role="politológ",
                    # Older versions were published earlier (30 days per version).
                    published_at=published_at - timedelta(days=30 * (len(versions) - version)),
                )
            )

    for t in data.GLOSSARY:
        _get_or_create(db, GlossaryTerm, {"slug": slugify(t["name"])}, t)

    db.commit()
