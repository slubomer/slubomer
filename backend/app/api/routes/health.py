"""Health checks for Docker, monitoring and quick manual tests."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.db import DbSession

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """The app is running. Does not touch the database."""
    return {"status": "ok"}


@router.get("/db")
def health_db(db: DbSession) -> dict[str, str]:
    """The app can reach the database."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
