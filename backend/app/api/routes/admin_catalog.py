"""Editorial management of documents, categories and the glossary.

The editor (redaktor) makes changes, the verifier (overovatel) may only read.
"""

from fastapi import APIRouter, status

from app.api.deps import EditorialUser, EditorUser
from app.core.db import DbSession
from app.schemas.admin import (
    CategoryAdminOut,
    CategoryCreate,
    CategoryUpdate,
    DocumentCreate,
    GlossaryTermAdminOut,
    GlossaryTermCreate,
    GlossaryTermUpdate,
)
from app.schemas.promise import DocumentOut
from app.services import catalog_service, document_service, glossary_service

router = APIRouter(prefix="/admin")


# --- Documents ---


@router.get("/documents", tags=["admin: documents"])
def list_documents(user: EditorialUser, db: DbSession) -> list[DocumentOut]:
    """Newest first."""
    return document_service.list_documents(db)


@router.post("/documents", status_code=status.HTTP_201_CREATED, tags=["admin: documents"])
def create_document(body: DocumentCreate, user: EditorUser, db: DbSession) -> DocumentOut:
    """Register a document by its metadata. File upload comes later (B-10)."""
    return document_service.create(db, user, body.model_dump())


# --- Categories ---


@router.get("/categories", tags=["admin: categories"])
def list_categories(user: EditorialUser, db: DbSession) -> list[CategoryAdminOut]:
    return catalog_service.list_categories_admin(db)


@router.post("/categories", status_code=status.HTTP_201_CREATED, tags=["admin: categories"])
def create_category(body: CategoryCreate, user: EditorUser, db: DbSession) -> CategoryAdminOut:
    return catalog_service.create_category(db, user, body.label, body.tagline)


@router.patch("/categories/{category_id}", tags=["admin: categories"])
def update_category(
    category_id: int, body: CategoryUpdate, user: EditorUser, db: DbSession
) -> CategoryAdminOut:
    """Rename or change the tagline. The slug stays the same."""
    values = body.model_dump(exclude_unset=True)
    return catalog_service.update_category(db, user, category_id, values)


# --- Glossary ---


@router.get("/glossary", tags=["admin: glossary"])
def list_terms(user: EditorialUser, db: DbSession) -> list[GlossaryTermAdminOut]:
    return glossary_service.list_terms(db)


@router.post("/glossary", status_code=status.HTTP_201_CREATED, tags=["admin: glossary"])
def create_term(body: GlossaryTermCreate, user: EditorUser, db: DbSession) -> GlossaryTermAdminOut:
    return glossary_service.create_term(db, user, body.model_dump())


@router.patch("/glossary/{term_id}", tags=["admin: glossary"])
def update_term(
    term_id: int, body: GlossaryTermUpdate, user: EditorUser, db: DbSession
) -> GlossaryTermAdminOut:
    """The slug stays the same, so links to the term keep working."""
    return glossary_service.update_term(db, user, term_id, body.model_dump(exclude_unset=True))
