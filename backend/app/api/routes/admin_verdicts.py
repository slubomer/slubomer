"""Verdicts for the political scientist: what is not verified yet, and verification.

AI verdicts are public right away. Verifying one marks it "overený politológom".
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import EditorialUser, VerifierUser
from app.core.db import DbSession
from app.models.enums import VerdictState, VerdictValue
from app.schemas.admin import PromiseAdminDetail
from app.schemas.common import Page
from app.schemas.verdict import VerdictQueueItem, VerifyRequest
from app.services import promise_admin_service, verdict_service
from app.services.verdict_service import QueueSort

router = APIRouter(prefix="/admin/verdicts", tags=["admin: verdicts"])


@router.get("")
def list_verdicts(
    user: EditorialUser,
    db: DbSession,
    verified: Annotated[bool | None, Query(description="false = ešte neoverené")] = None,
    value: VerdictValue | None = None,
    state: Annotated[VerdictState | None, Query(description="publikovany alebo navrh")] = None,
    subject: Annotated[str | None, Query(description="Slug subjektu")] = None,
    max_confidence: Annotated[
        float | None, Query(ge=0, le=1, description="Len verdikty s istotou AI najviac takouto")
    ] = None,
    sort: Annotated[
        QueueSort, Query(description="oldest = najstaršie, confidence = najmenej isté prvé")
    ] = "oldest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[VerdictQueueItem]:
    """Current verdict of each promise (published or draft)."""
    return verdict_service.queue(
        db,
        verified=verified,
        value=value,
        state=state,
        subject=subject,
        max_confidence=max_confidence,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post("/{verdict_id}/verify")
def verify_verdict(
    verdict_id: int, body: VerifyRequest, user: VerifierUser, db: DbSession
) -> PromiseAdminDetail:
    """Mark the verdict as verified by a political scientist (new published version).

    Only the political scientist (overovatel) may verify, not an admin (403).
    The reason is required. Value and explanation may be corrected at the same time.
    Needs evidence from a published document, except for "nesplnene".
    """
    verdict = verdict_service.verify(
        db, user, verdict_id, body.reason, value=body.value, explanation=body.explanation
    )
    return promise_admin_service.get_detail(db, verdict.promise_id)
