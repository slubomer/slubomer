"""Verdict queue and verification by a political scientist (/api/v1/admin/verdicts)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import VerdictState, VerdictValue
from app.schemas.admin import Reason
from app.schemas.catalog import SubjectOut
from app.schemas.common import ApiModel


class PromiseRef(ApiModel):
    id: int
    slug: str
    title: str
    subject: SubjectOut


class VerdictQueueItem(ApiModel):
    id: int
    version: int
    value: VerdictValue
    explanation: str
    state: VerdictState
    confidence: float | None
    ai_generated: bool
    verified: bool
    reviewer_role: str | None
    published_at: datetime | None
    promise: PromiseRef


class VerifyRequest(BaseModel):
    """Verify a verdict. Send value or explanation only to correct them."""

    reason: Reason = Field(description="Prečo politológ verdikt potvrdzuje alebo mení")
    value: VerdictValue | None = None
    explanation: str | None = Field(default=None, min_length=1)
