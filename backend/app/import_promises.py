"""Import promises from a JSON file (format of data/sluby.json).

Each record: {"strana": ..., "nazov": ..., "telo": ..., "datum": ..., "stav": ...}
and optionally "kategoria" (topic, e.g. "Zdravotníctvo").
Promises are imported as drafts (navrh) without a verdict, so they are not public
yet: an editor first adds the verbatim quote, page and document, then approves them.
"stav" is ignored, it is only a placeholder in the draft file format.

Safe to run repeatedly: promises already in the database are skipped, but they
get a category if the file has one and they don't have it yet.

Usage (in backend/): python -m app.import_promises ../data/sluby.json
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.text import normalize, slugify, unique_slug
from app.models import Category, Promise, Subject
from app.models.enums import PromiseState
from app.services import audit

CATEGORY_FIELD = "kategoria"  # optional field with the promise's topic


@dataclass
class ImportResult:
    created: int = 0
    categorized: int = 0  # existing promises that got their category now
    skipped: int = 0  # already in the database or a duplicate in the file


def _short_name(party: str) -> str | None:
    """'SMER – slovenská sociálna demokracia' -> 'SMER'; no short name otherwise."""
    head, sep, _ = party.partition(" – ")
    return head.strip() if sep else None


def _get_subject(db: Session, cache: dict[str, Subject], party: str) -> Subject:
    slug = slugify(party)
    if slug not in cache:
        subject = db.scalar(select(Subject).where(Subject.slug == slug))
        if subject is None:
            subject = Subject(slug=slug, name=party, short_name=_short_name(party))
            db.add(subject)
            db.flush()
        cache[slug] = subject
    return cache[slug]


def _get_category(db: Session, cache: dict[str, Category], label: str) -> Category | None:
    """Category by its name; created the first time it appears. None if empty."""
    slug = slugify(label)
    if not slug:
        return None
    if slug not in cache:
        category = db.scalar(select(Category).where(Category.slug == slug))
        if category is None:
            category = Category(slug=slug, label=label)
            db.add(category)
            db.flush()
        cache[slug] = category
    return cache[slug]


def import_promises(db: Session, records: list[dict], source: str = "") -> ImportResult:
    result = ImportResult()
    subjects: dict[str, Subject] = {}
    categories: dict[str, Category] = {}

    # Loaded once up front, so the import doesn't run a query per record.
    taken_slugs = set(db.scalars(select(Promise.slug)))
    existing = {(p.subject_id, normalize(p.description)): p for p in db.scalars(select(Promise))}

    for record in records:
        party, title, text = (
            record["strana"].strip(),
            record["nazov"].strip(),
            record["telo"].strip(),
        )
        subject = _get_subject(db, subjects, party)
        category = _get_category(db, categories, (record.get(CATEGORY_FIELD) or "").strip())

        key = (subject.id, normalize(text))
        if key in existing:
            known = existing[key]
            # A newer file may bring categories for promises imported earlier.
            if category and known.category is None:
                known.category = category
                known.refresh_search_text()
                result.categorized += 1
            else:
                result.skipped += 1
            continue

        # Titles repeat across parties, so the party is added when needed.
        slug = unique_slug(slugify(title), subject.slug, taken_slugs)
        promise = Promise(
            slug=slug,
            subject=subject,
            category=category,
            title=title,
            description=text,
            # A draft until the editors add the quote, page and document and approve it.
            state=PromiseState.NAVRH,
        )
        promise.refresh_search_text()
        db.add(promise)
        taken_slugs.add(slug)
        existing[key] = promise
        result.created += 1

    # One summary entry for the whole import, not one per promise.
    if result.created or result.categorized:
        audit.record(
            db,
            None,
            "import",
            "promise",
            None,
            after={
                "created": result.created,
                "categorized": result.categorized,
                "skipped": result.skipped,
                "source": source,
            },
        )
    db.commit()
    return result


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m app.import_promises <path/to/sluby.json>")
    records = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    with SessionLocal() as db:
        result = import_promises(db, records, source=Path(sys.argv[1]).name)
    print(
        f"Promises imported: {result.created}, categorized: {result.categorized}, "
        f"skipped: {result.skipped}"
    )


if __name__ == "__main__":
    main()
