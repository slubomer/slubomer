"""Subjects and categories: lookup lists for filters, category management."""

from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.text import slugify
from app.models import Category, Promise, Subject, User
from app.models.enums import PromiseState
from app.schemas.catalog import CategoryWithCount, SubjectWithCount
from app.services import audit
from app.services.errors import Conflict, Invalid, NotFound

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


def create_category(db: Session, actor: User, label: str, tagline: str | None) -> Category:
    slug = slugify(label, max_length=100)
    if db.scalar(select(Category.id).where(Category.slug == slug)):
        raise Conflict(f"Kategória '{slug}' už existuje")
    category = Category(slug=slug, label=label.strip(), tagline=tagline)
    db.add(category)
    db.flush()
    audit.record(db, actor, "create", "category", category.id, after=audit.snapshot(category))
    db.commit()
    return category


def update_category(db: Session, actor: User, category_id: int, values: dict[str, Any]) -> Category:
    """Rename or change the tagline. The slug stays, so existing links keep working."""
    category = db.get(Category, category_id)
    if category is None:
        raise NotFound("Kategória sa nenašla")
    if "label" in values and values["label"] is None:
        raise Invalid("Kategória musí mať názov")
    if audit.apply_changes(db, actor, category, "category", values):
        # The category name is part of the search text of its promises.
        for promise in db.scalars(select(Promise).where(Promise.category_id == category.id)):
            promise.refresh_search_text()
    db.commit()
    return category


def list_categories_admin(db: Session) -> list[Category]:
    """With ids, for editing (the public list has only slugs)."""
    return list(db.scalars(select(Category).order_by(Category.label)))
