"""Import promises from the JSON file (format: app/schemas/promise_import.py).

Used by the command line (app/import_promises.py) and by the editorial API.

- Promises come in as drafts (navrh). Editors approve them before they go public.
- "stav" + "zdovodnenie" become a verdict draft (navrh) waiting for the verifier.
- "vyhodnotenie" becomes evidence: votes and web pages, each with its own document.
- Safe to run repeatedly. A promise already in the database (same party and text)
  only gets what is new: empty fields filled in, new evidence, and a new verdict
  version when the state or reason changed. Filled-in fields are never overwritten.
"""

from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.text import normalize, slugify, unique_slug
from app.models import Category, Document, Evidence, Promise, Subject, User, Verdict
from app.models.enums import DocumentKind, EvidenceRole, PromiseState, VerdictState
from app.schemas.promise_import import (
    EvidenceIn,
    ImportResultOut,
    PromiseImportFile,
    PromiseIn,
)
from app.services import audit

# Promise fields filled from the file when they are still empty.
FILLABLE_FIELDS = ("quote", "page", "document", "type", "category")


class _Importer:
    """Holds lookups for one import run, so each row isn't a new query."""

    def __init__(self, db: Session, ai_generated: bool) -> None:
        self.db = db
        self.ai_generated = ai_generated
        self.result = ImportResultOut()
        self.subjects: dict[str, Subject] = {}
        self.categories: dict[str, Category] = {}
        self.documents: dict[tuple, Document] = {}
        self.taken_slugs = set(db.scalars(select(Promise.slug)))
        self.existing = {
            (p.subject_id, normalize(p.description)): p
            for p in db.scalars(
                select(Promise).options(
                    selectinload(Promise.evidence), selectinload(Promise.verdicts)
                )
            )
        }
        self.created_now: set[tuple] = set()

    # --- Lookups (found or created) -----------------------------------------

    def subject(self, party: str) -> Subject:
        slug = slugify(party)
        if slug not in self.subjects:
            subject = self.db.scalar(select(Subject).where(Subject.slug == slug))
            if subject is None:
                subject = Subject(slug=slug, name=party, short_name=_short_name(party))
                self.db.add(subject)
                self.db.flush()
            self.subjects[slug] = subject
        return self.subjects[slug]

    def category(self, label: str | None) -> Category | None:
        slug = slugify(label or "")
        if not slug:
            return None
        if slug not in self.categories:
            category = self.db.scalar(select(Category).where(Category.slug == slug))
            if category is None:
                category = Category(slug=slug, label=label.strip())
                self.db.add(category)
                self.db.flush()
            self.categories[slug] = category
        return self.categories[slug]

    def document(self, kind: DocumentKind, title: str, url: str | None, **extra) -> Document:
        """A document is the same when the URL matches, or kind and title without a URL."""
        key = (url,) if url else (kind, title)
        if key not in self.documents:
            stmt = select(Document).where(Document.url == url)
            if not url:
                stmt = select(Document).where(
                    Document.kind == kind, Document.title == title, Document.url.is_(None)
                )
            document = self.db.scalars(stmt.limit(1)).first()
            if document is None:
                document = Document(kind=kind, title=title, url=url, **extra)
                self.db.add(document)
                self.db.flush()
            self.documents[key] = document
        return self.documents[key]

    def program(self, record: PromiseIn) -> Document | None:
        if not (record.zdroj or record.program_url):
            return None
        title = (record.zdroj or record.program_url).strip()
        return self.document(DocumentKind.PROGRAM, title, record.program_url)

    def evidence_document(self, item: EvidenceIn) -> Document:
        if item.typ == "hlasovanie":
            kind, title = DocumentKind.HLASOVANIE, "Hlasovanie NR SR"
            if item.datum:
                title += f" {item.datum.strftime('%d. %m. %Y')}"
        else:
            kind = DocumentKind.WEB
            title = urlparse(item.zdroj).netloc.removeprefix("www.") or item.zdroj
        return self.document(kind, title, item.zdroj, published_at=item.datum)

    # --- One record ---------------------------------------------------------

    def add(self, record: PromiseIn) -> None:
        subject = self.subject(record.strana.strip())
        fields = {
            "quote": (record.citacia or "").strip() or None,
            "page": record.strana_programu,
            "document": self.program(record),
            "type": record.typ,
            "category": self.category(record.tema),
        }
        key = (subject.id, normalize(record.telo))

        if key in self.created_now:
            self.result.skipped += 1  # the same promise twice in one file
            return
        promise = self.existing.get(key)
        if promise is None:
            promise = self._create(record, subject, fields)
            self.created_now.add(key)
            self.existing[key] = promise
            changed = True
        else:
            changed = self._fill_empty(promise, fields)

        changed |= self._add_evidence(promise, record.vyhodnotenie)
        changed |= self._add_verdict(promise, record)

        if key not in self.created_now:
            if changed:
                self.result.updated += 1
            else:
                self.result.skipped += 1

    def _create(self, record: PromiseIn, subject: Subject, fields: dict) -> Promise:
        title = record.nazov.strip()
        # Titles repeat across parties, so the party is added when needed.
        slug = unique_slug(slugify(title), subject.slug, self.taken_slugs)
        promise = Promise(
            slug=slug,
            subject=subject,
            title=title,
            description=record.telo.strip(),
            state=PromiseState.NAVRH,  # public only after an editor approves it
            ai_generated=self.ai_generated,
            **fields,
        )
        promise.refresh_search_text()
        self.db.add(promise)
        self.taken_slugs.add(slug)
        self.result.created += 1
        return promise

    def _fill_empty(self, promise: Promise, fields: dict) -> bool:
        """Fill only empty fields: what editors already filled in stays as it is."""
        changed = False
        for name in FILLABLE_FIELDS:
            if fields[name] is not None and getattr(promise, name) is None:
                setattr(promise, name, fields[name])
                changed = True
        if changed:
            promise.refresh_search_text()
        return changed

    def _add_evidence(self, promise: Promise, items: list[EvidenceIn]) -> bool:
        known = {e.document_id for e in promise.evidence}
        added = False
        for item in items:
            document = self.evidence_document(item)
            if document.id in known:
                continue
            promise.evidence.append(
                Evidence(
                    document=document,
                    role=EvidenceRole.PODKLAD,
                    vote=item.hlasovanie.model_dump() if item.hlasovanie else None,
                    ai_generated=self.ai_generated,
                )
            )
            known.add(document.id)
            self.result.evidence += 1
            added = True
        return added

    def _add_verdict(self, promise: Promise, record: PromiseIn) -> bool:
        """A new draft version when the state or reason differs from the latest version."""
        if record.stav is None:
            return False
        explanation = record.zdovodnenie.strip()
        latest = max(promise.verdicts, key=lambda v: v.version, default=None)
        if latest and latest.value == record.stav and latest.explanation == explanation:
            return False

        # An older draft nobody reviewed yet is replaced, so the verifier sees one draft.
        for verdict in promise.verdicts:
            if verdict.state == VerdictState.NAVRH:
                verdict.state = VerdictState.NAHRADENY
        promise.verdicts.append(
            Verdict(
                version=(latest.version + 1) if latest else 1,
                value=record.stav,
                explanation=explanation,
                confidence=record.confidence,
                state=VerdictState.NAVRH,
                ai_generated=self.ai_generated,
            )
        )
        self.result.verdicts += 1
        return True


def _short_name(party: str) -> str | None:
    """'SMER – slovenská sociálna demokracia' -> 'SMER'; no short name otherwise."""
    head, sep, _ = party.partition(" – ")
    return head.strip() if sep else None


def import_file(
    db: Session, data: PromiseImportFile, actor: User | None = None, source: str = ""
) -> ImportResultOut:
    """Import a validated file in one transaction, with one audit entry for the whole run."""
    importer = _Importer(db, ai_generated=data.meta.generovane_ai)
    for record in data.sluby:
        importer.add(record)
    result = importer.result

    if result.created or result.updated:
        audit.record(
            db,
            actor,
            "import",
            "promise",
            None,
            after={
                **result.model_dump(),
                "source": source,
                "meta": data.meta.model_dump(mode="json"),
            },
        )
    db.commit()
    return result
