"""Database connection and session handling."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# pool_pre_ping drops dead connections instead of failing the request.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class for all database tables (see app/models/)."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    with SessionLocal() as session:
        yield session


# Use in routes as a parameter type: def route(db: DbSession): ...
DbSession = Annotated[Session, Depends(get_db)]
