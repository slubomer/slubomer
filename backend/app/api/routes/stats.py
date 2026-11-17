"""Overview charts (F-01)."""

from fastapi import APIRouter

from app.core.db import DbSession
from app.schemas.stats import OverviewStats, SubjectStats
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def overview(db: DbSession) -> OverviewStats:
    """Number of public promises and how many have each verdict."""
    return stats_service.overview(db)


@router.get("/subjects")
def by_subject(db: DbSession) -> list[SubjectStats]:
    """The same numbers per subject ("Kto plní sľuby?")."""
    return stats_service.by_subject(db)
