"""Lookup lists for filters: subjects and categories."""

from fastapi import APIRouter

from app.core.db import DbSession
from app.schemas.catalog import CategoryWithCount, SubjectWithCount
from app.services import catalog_service

router = APIRouter(tags=["catalog"])


@router.get("/subjects")
def list_subjects(db: DbSession) -> list[SubjectWithCount]:
    return catalog_service.list_subjects(db)


@router.get("/categories")
def list_categories(db: DbSession) -> list[CategoryWithCount]:
    return catalog_service.list_categories(db)
