"""Requests and responses of the editorial API (/api/v1/admin/...)."""

from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, TypeAdapter

from app.models.enums import (
    DocumentKind,
    EvidenceRole,
    PromiseState,
    PromiseType,
    VerdictState,
    VerdictValue,
)
from app.schemas.catalog import CategoryOut, SubjectOut
from app.schemas.common import ApiModel
from app.schemas.promise import DocumentOut

# A reason that goes to the audit log: short, but not empty.
Reason = Annotated[str, Field(min_length=3, max_length=1000)]
Title = Annotated[str, Field(min_length=1, max_length=300)]
Page = Annotated[int, Field(ge=1)]
_HTTP_URL = TypeAdapter(HttpUrl)


def _check_url(value: str) -> str:
    return str(_HTTP_URL.validate_python(value))


# Checked as a URL, stored as plain text.
Url = Annotated[str, AfterValidator(_check_url)]


# --- Promises ---------------------------------------------------------------


class EvidenceAdminOut(ApiModel):
    id: int
    role: EvidenceRole
    page: int | None
    quote: str
    ai_generated: bool
    document: DocumentOut


class VerdictAdminOut(ApiModel):
    """Every version, including drafts the public never sees."""

    id: int
    version: int
    value: VerdictValue
    explanation: str
    state: VerdictState
    confidence: float | None
    ai_generated: bool
    reviewer_role: str | None
    review_reason: str | None
    created_at: datetime
    published_at: datetime | None


class CommentAdminOut(ApiModel):
    id: int
    author_id: int | None  # None when the author's account was deleted
    author_role: str
    text: str
    created_at: datetime
    updated_at: datetime | None


class PromiseAdminItem(ApiModel):
    id: int
    slug: str
    title: str
    state: PromiseState
    type: PromiseType | None
    ai_generated: bool
    subject: SubjectOut
    category: CategoryOut | None
    created_at: datetime


class PromiseAdminDetail(PromiseAdminItem):
    description: str
    quote: str | None
    page: int | None
    document: DocumentOut | None
    evidence: list[EvidenceAdminOut]
    verdicts: list[VerdictAdminOut]  # newest first
    comments: list[CommentAdminOut]  # oldest first


class PromiseCreate(BaseModel):
    """A promise added by hand. It starts as a draft (navrh)."""

    subject: str = Field(description="Slug subjektu, napr. smer-slovenska-socialna-demokracia")
    title: Title
    description: str = Field(min_length=1)
    category: str | None = Field(default=None, description="Slug kategórie")
    type: PromiseType | None = None
    document_id: int | None = None
    quote: str | None = None
    page: Page | None = None


class PromiseUpdate(BaseModel):
    """Only the sent fields change; null clears a field.

    Changing a quote or page that is already filled in needs a reason.
    """

    subject: str | None = None
    title: Title | None = None
    description: str | None = Field(default=None, min_length=1)
    category: str | None = None
    type: PromiseType | None = None
    document_id: int | None = None
    quote: str | None = None
    page: Page | None = None
    reason: Reason | None = None


class RejectRequest(BaseModel):
    reason: Reason


class EvidenceCreate(BaseModel):
    document_id: int
    role: EvidenceRole
    quote: str = Field(min_length=1)
    page: Page | None = None


class CommentWrite(BaseModel):
    """New text of a comment (used for both create and update)."""

    text: str = Field(min_length=1, max_length=5000)


# --- Documents --------------------------------------------------------------


class DocumentCreate(BaseModel):
    """Metadata only. Uploading the file and its hash come with B-10."""

    kind: DocumentKind
    title: Title
    url: Url | None = None
    published_at: date | None = None


# --- Categories -------------------------------------------------------------


class CategoryAdminOut(ApiModel):
    id: int
    slug: str
    label: str
    tagline: str | None


class CategoryCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    tagline: str | None = Field(default=None, max_length=200)


class CategoryUpdate(BaseModel):
    """The slug stays the same, so links with ?category=... keep working."""

    label: str | None = Field(default=None, min_length=1, max_length=100)
    tagline: str | None = Field(default=None, max_length=200)


# --- Glossary ---------------------------------------------------------------


class GlossaryTermAdminOut(ApiModel):
    id: int
    slug: str
    name: str
    short: str
    long: str | None
    example: str
    wiki_url: str | None
    stems: list[str]


class GlossaryTermCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    short: str = Field(min_length=1, max_length=300)
    long: str | None = None
    example: str = Field(min_length=1, max_length=300)
    wiki_url: Url | None = None
    stems: list[str] = Field(default_factory=list, description="Začiatky slov na zvýraznenie")


class GlossaryTermUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    short: str | None = Field(default=None, min_length=1, max_length=300)
    long: str | None = None
    example: str | None = Field(default=None, min_length=1, max_length=300)
    wiki_url: Url | None = None
    stems: list[str] | None = None
