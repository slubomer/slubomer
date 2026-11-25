"""Reading promises for the public web: list with filters and detail."""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Select, and_, exists, func, select
from sqlalchemy.orm import Session, contains_eager, selectinload

from app.core.text import normalize
from app.models import Category, Evidence, Promise, PromiseComment, Subject, Verdict
from app.models.enums import PromiseState, PromiseType, VerdictState, VerdictValue
from app.schemas.common import Page
from app.schemas.promise import (
    CommentOut,
    PromiseDetail,
    PromiseListItem,
    VerdictShort,
    VerdictVersion,
)

SortOption = Literal["verified", "title"]


@dataclass
class PromiseFilters:
    q: str | None = None
    subject: str | None = None  # subject slug
    category: str | None = None  # category slug
    verdict: VerdictValue | None = None
    type: PromiseType | None = None


# True when a political scientist commented on the promise ("dovysvetlené").
_EXPLAINED = exists().where(PromiseComment.promise_id == Promise.id).label("explained")


def _public_select() -> Select:
    """Approved promises with their published verdict (if any) and the explained flag."""
    return (
        select(Promise, Verdict, _EXPLAINED)
        .join(Promise.subject)
        .outerjoin(Promise.category)  # promises without a category stay in the list
        .outerjoin(
            Verdict,
            and_(Verdict.promise_id == Promise.id, Verdict.state == VerdictState.PUBLIKOVANY),
        )
        .where(Promise.state == PromiseState.SCHVALENY)
    )


def _apply_filters(stmt: Select, f: PromiseFilters) -> Select:
    if f.subject:
        stmt = stmt.where(Subject.slug == f.subject)
    if f.category:
        stmt = stmt.where(Category.slug == f.category)
    if f.verdict:
        stmt = stmt.where(Verdict.value == f.verdict)
    if f.type:
        stmt = stmt.where(Promise.type == f.type)
    if f.q and (needle := normalize(f.q)):
        stmt = stmt.where(Promise.search_text.contains(needle, autoescape=True))
    return stmt


def _list_item(promise: Promise, verdict: Verdict | None, explained: bool) -> PromiseListItem:
    return PromiseListItem(
        slug=promise.slug,
        title=promise.title,
        type=promise.type,
        subject=promise.subject,
        category=promise.category,
        verdict=VerdictShort.model_validate(verdict) if verdict else None,
        explained=explained,
    )


def search(
    db: Session,
    filters: PromiseFilters,
    page: int = 1,
    page_size: int = 20,
    sort: SortOption = "verified",
) -> Page[PromiseListItem]:
    """Filtered, paginated list of public promises."""
    stmt = _apply_filters(_public_select(), filters)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    if sort == "title":
        stmt = stmt.order_by(Promise.title, Promise.id)  # id keeps pages stable for equal titles
    else:
        # Freshly verified first, promises without a verdict at the end.
        stmt = stmt.order_by(Verdict.published_at.desc().nulls_last(), Promise.id)

    stmt = (
        stmt.options(contains_eager(Promise.subject), contains_eager(Promise.category))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(stmt).all()

    return Page(
        items=[_list_item(p, v, explained) for p, v, explained in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_detail(db: Session, slug: str) -> PromiseDetail | None:
    """Full detail of one public promise, or None if it doesn't exist or isn't approved."""
    promise = db.scalar(
        select(Promise)
        .where(Promise.slug == slug, Promise.state == PromiseState.SCHVALENY)
        .options(
            selectinload(Promise.subject),
            selectinload(Promise.category),
            selectinload(Promise.document),
            selectinload(Promise.evidence).selectinload(Evidence.document),
            selectinload(Promise.verdicts),
            selectinload(Promise.comments),
        )
    )
    if promise is None:
        return None

    # Only versions that were ever public; drafts and returned versions stay internal.
    published = [v for v in promise.verdicts if v.published_at is not None]
    current = next((v for v in published if v.state == VerdictState.PUBLIKOVANY), None)

    item = _list_item(promise, current, explained=bool(promise.comments))
    return PromiseDetail(
        **item.model_dump(),
        description=promise.description,
        quote=promise.quote,
        page=promise.page,
        ai_generated=promise.ai_generated,
        document=promise.document,
        evidence=promise.evidence,
        history=[VerdictVersion.model_validate(v) for v in published],
        comments=[CommentOut.model_validate(c) for c in promise.comments],
    )
