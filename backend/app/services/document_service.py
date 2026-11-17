"""Registry of documents (programmes, laws, ...) that evidence points to.

For now only metadata. Uploading the file, its hash and archive come with B-10.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, User
from app.services import audit


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.id.desc())))


def create(db: Session, actor: User, values: dict[str, Any]) -> Document:
    document = Document(**values)
    db.add(document)
    db.flush()  # assigns document.id for the audit entry
    audit.record(db, actor, "create", "document", document.id, after=audit.snapshot(document))
    db.commit()
    return document
