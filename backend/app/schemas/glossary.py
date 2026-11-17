"""Glossary responses."""

from app.schemas.common import ApiModel


class GlossaryTermOut(ApiModel):
    slug: str
    name: str
    short: str
    long: str | None
    example: str
    wiki_url: str | None
    stems: list[str]
