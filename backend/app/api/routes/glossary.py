"""Glossary of political terms."""

from fastapi import APIRouter, HTTPException

from app.core.db import DbSession
from app.schemas.glossary import GlossaryTermOut
from app.services import glossary_service

router = APIRouter(prefix="/glossary", tags=["glossary"])


@router.get("")
def list_terms(db: DbSession) -> list[GlossaryTermOut]:
    """All terms in Slovak alphabetical order."""
    return glossary_service.list_terms(db)


@router.get("/{slug}")
def get_term(slug: str, db: DbSession) -> GlossaryTermOut:
    term = glossary_service.get_term(db, slug)
    if term is None:
        raise HTTPException(status_code=404, detail="Pojem sa nenašiel")
    return term
