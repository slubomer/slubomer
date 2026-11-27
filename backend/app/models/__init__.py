"""Database tables, one module per table.

Import every model here so Alembic can see it when generating migrations.
"""

from app.core.db import Base
from app.models.category import Category
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.glossary_term import GlossaryTerm
from app.models.promise import Promise
from app.models.subject import Subject
from app.models.user import User, UserSession
from app.models.verdict import Verdict

__all__ = [
    "Base",
    "Category",
    "Document",
    "Evidence",
    "GlossaryTerm",
    "Promise",
    "Subject",
    "User",
    "UserSession",
    "Verdict",
]
