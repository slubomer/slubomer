"""Lookup lists used by filters: subjects and categories."""

from app.schemas.common import ApiModel


class SubjectOut(ApiModel):
    slug: str
    name: str
    short_name: str | None


class CategoryOut(ApiModel):
    slug: str
    label: str
    tagline: str | None


class SubjectWithCount(SubjectOut):
    promise_count: int


class CategoryWithCount(CategoryOut):
    promise_count: int
