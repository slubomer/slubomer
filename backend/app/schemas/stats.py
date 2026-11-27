"""Numbers for the overview charts."""

from pydantic import BaseModel

from app.schemas.catalog import SubjectOut


class VerdictCounts(BaseModel):
    splnene: int = 0
    ciastocne: int = 0
    porusene: int = 0
    nesplnene: int = 0


class OverviewStats(BaseModel):
    total: int
    by_verdict: VerdictCounts
    unrated: int  # promises without a published verdict yet


class SubjectStats(BaseModel):
    subject: SubjectOut
    total: int
    by_verdict: VerdictCounts
    unrated: int
