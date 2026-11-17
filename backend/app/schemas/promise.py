"""Promise list and detail responses."""

from datetime import date, datetime

from app.models.enums import DocumentKind, EvidenceRole, PromiseType, VerdictValue
from app.schemas.catalog import CategoryOut, SubjectOut
from app.schemas.common import ApiModel


class VerdictShort(ApiModel):
    value: VerdictValue
    explanation: str
    published_at: datetime | None


class VerdictVersion(VerdictShort):
    version: int
    reviewer_role: str | None
    ai_generated: bool


class DocumentOut(ApiModel):
    id: int
    kind: DocumentKind
    title: str
    url: str | None
    published_at: date | None


class EvidenceOut(ApiModel):
    role: EvidenceRole
    page: int | None
    quote: str
    ai_generated: bool
    document: DocumentOut


class PromiseListItem(ApiModel):
    slug: str
    title: str
    type: PromiseType
    subject: SubjectOut
    category: CategoryOut
    verdict: VerdictShort | None


class PromiseDetail(PromiseListItem):
    quote: str
    page: int | None
    ai_generated: bool
    document: DocumentOut | None
    evidence: list[EvidenceOut]
    # All published versions, newest first.
    history: list[VerdictVersion]
