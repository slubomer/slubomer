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


class VoteOut(ApiModel):
    """Vote in the National Council. Field names as in the imported JSON."""

    faza: str  # e.g. finalne, prve_citanie
    vysledok: str  # e.g. Návrh prešiel
    strana_za: int  # the party's MPs who voted for it
    clenov_strany: int  # MPs in the party's club
    celkom_za: int
    pritomnych: int


class EvidenceOut(ApiModel):
    role: EvidenceRole
    page: int | None
    quote: str | None  # empty for votes and imported web links
    vote: VoteOut | None
    ai_generated: bool
    document: DocumentOut


class CommentOut(ApiModel):
    """A political scientist's comment. Role only, no name (GDPR)."""

    author_role: str
    text: str
    created_at: datetime
    updated_at: datetime | None


class PromiseListItem(ApiModel):
    slug: str
    title: str
    type: PromiseType | None  # None = not classified yet
    subject: SubjectOut
    category: CategoryOut | None  # None = not classified yet
    verdict: VerdictShort | None  # None = not rated yet
    # A political scientist commented on it ("dovysvetlené").
    # This is not the same as a verdict approved by a political scientist.
    explained: bool


class PromiseDetail(PromiseListItem):
    description: str
    quote: str | None  # verbatim from the programme, once it is extracted
    page: int | None
    ai_generated: bool
    document: DocumentOut | None
    evidence: list[EvidenceOut]
    # All published versions, newest first.
    history: list[VerdictVersion]
    # All comments by political scientists, oldest first.
    comments: list[CommentOut]
