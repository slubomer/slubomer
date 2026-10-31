"""Database tables, one module per table.

Import every model here so Alembic can see it when generating migrations.
"""

from app.core.db import Base

__all__ = ["Base"]
