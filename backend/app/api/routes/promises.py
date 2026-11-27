"""Public promise list and detail (F-02, F-03)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.core.db import DbSession
from app.models.enums import PromiseType, VerdictValue
from app.schemas.common import Page
from app.schemas.promise import PromiseDetail, PromiseListItem
from app.services import promise_service
from app.services.promise_service import PromiseFilters, SortOption

router = APIRouter(prefix="/promises", tags=["promises"])


@router.get("")
def list_promises(
    db: DbSession,
    q: Annotated[str | None, Query(description="Hľadaný text, diakritika nevadí")] = None,
    subject: Annotated[str | None, Query(description="Slug subjektu")] = None,
    category: Annotated[str | None, Query(description="Slug kategórie")] = None,
    verdict: VerdictValue | None = None,
    verified: Annotated[
        bool | None, Query(description="true = overené politológom, false = len AI")
    ] = None,
    type: PromiseType | None = None,
    sort: SortOption = "verified",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[PromiseListItem]:
    """Approved promises with their published verdict."""
    filters = PromiseFilters(
        q=q, subject=subject, category=category, verdict=verdict, verified=verified, type=type
    )
    return promise_service.search(db, filters, page=page, page_size=page_size, sort=sort)


@router.get("/{slug}")
def get_promise(slug: str, db: DbSession) -> PromiseDetail:
    """One promise with its quote, evidence and verdict history."""
    detail = promise_service.get_detail(db, slug)
    if detail is None:
        raise HTTPException(status_code=404, detail="Sľub sa nenašiel")
    return detail
