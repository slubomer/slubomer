"""Lookup lists for filters, each with the number of public promises."""

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Category, Promise, Subject
from app.models.enums import PromiseState
from app.schemas.catalog import CategoryWithCount, SubjectWithCount

_PUBLIC = Promise.state == PromiseState.SCHVALENY


def list_subjects(db: Session) -> list[SubjectWithCount]:
    rows = db.execute(
        select(Subject, func.count(Promise.id))
        .outerjoin(Promise, and_(Promise.subject_id == Subject.id, _PUBLIC))
        .group_by(Subject.id)
        .order_by(Subject.name)
    ).all()
    return [
        SubjectWithCount(slug=s.slug, name=s.name, short_name=s.short_name, promise_count=n)
        for s, n in rows
    ]


def list_categories(db: Session) -> list[CategoryWithCount]:
    rows = db.execute(
        select(Category, func.count(Promise.id))
        .outerjoin(Promise, and_(Promise.category_id == Category.id, _PUBLIC))
        .group_by(Category.id)
        .order_by(Category.label)
    ).all()
    return [
        CategoryWithCount(slug=c.slug, label=c.label, tagline=c.tagline, promise_count=n)
        for c, n in rows
    ]
