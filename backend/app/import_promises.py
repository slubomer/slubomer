"""Import promises from a JSON file (format of data/sluby.json).

Each record: {"strana": ..., "nazov": ..., "telo": ..., "datum": ..., "stav": ...}.
Promises are imported as drafts (navrh) without a verdict, so they are not public
yet: an editor first adds the verbatim quote, page and document, then approves them.
"stav" is ignored, it is only a placeholder in the draft file format.

Safe to run repeatedly: promises already in the database are skipped.

Usage (in backend/): python -m app.import_promises ../data/sluby.json
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.text import normalize, slugify
from app.models import Promise, Subject
from app.models.enums import PromiseState


@dataclass
class ImportResult:
    created: int = 0
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


def _unique_slug(base: str, subject_slug: str, taken: set[str]) -> str:
    """Promise titles can repeat across parties, so add the party, then a number."""
    for candidate in (base, f"{base}-{subject_slug}"):
        if candidate not in taken:
            return candidate
    n = 2
    while f"{base}-{subject_slug}-{n}" in taken:
        n += 1
    return f"{base}-{subject_slug}-{n}"


def import_promises(db: Session, records: list[dict]) -> ImportResult:
    result = ImportResult()
    subjects: dict[str, Subject] = {}

    # Loaded once up front, so the import doesn't run a query per record.
    taken_slugs = set(db.scalars(select(Promise.slug)))
    existing = {
        (sid, normalize(text))
        for sid, text in db.execute(select(Promise.subject_id, Promise.description))
    }

    for record in records:
        party, title, text = (
            record["strana"].strip(),
            record["nazov"].strip(),
            record["telo"].strip(),
        )
        subject = _get_subject(db, subjects, party)

        key = (subject.id, normalize(text))
        if key in existing:
            result.skipped += 1
            continue

        slug = _unique_slug(slugify(title), subject.slug, taken_slugs)
        db.add(
            Promise(
                slug=slug,
                subject_id=subject.id,
                title=title,
                description=text,
                # A draft until the editors add the quote, page and document and approve it.
                state=PromiseState.NAVRH,
                search_text=normalize(f"{title} {text} {party}"),
            )
        )
        taken_slugs.add(slug)
        existing.add(key)
        result.created += 1

    db.commit()
    return result


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m app.import_promises <path/to/sluby.json>")
    records = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    with SessionLocal() as db:
        result = import_promises(db, records)
    print(f"Promises imported: {result.created}, skipped: {result.skipped}")


if __name__ == "__main__":
    main()
