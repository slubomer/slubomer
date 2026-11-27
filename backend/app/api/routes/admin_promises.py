"""Editorial work on promises and their evidence.

The editor (redaktor) makes changes, the verifier (overovatel) may only read,
except for comments: those are written by the verifier (political scientist).
"""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import EditorialUser, EditorUser, VerifierUser
from app.core.db import DbSession
from app.models.enums import PromiseState
from app.schemas.admin import (
    CommentWrite,
    EvidenceCreate,
    PromiseAdminDetail,
    PromiseAdminItem,
    PromiseCreate,
    PromiseUpdate,
    RejectRequest,
)
from app.schemas.common import Page
from app.services import comment_service
from app.services import promise_admin_service as service

router = APIRouter(prefix="/admin/promises", tags=["admin: promises"])


@router.get("")
def list_promises(
    user: EditorialUser,
    db: DbSession,
    state: PromiseState | None = None,
    subject: Annotated[str | None, Query(description="Slug subjektu")] = None,
    category: Annotated[str | None, Query(description="Slug kategórie")] = None,
    without_category: Annotated[bool, Query(description="Len sľuby bez kategórie")] = False,
    q: Annotated[str | None, Query(description="Hľadaný text")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[PromiseAdminItem]:
    """All promises including drafts and rejected ones, oldest first."""
    return service.search(
        db,
        state=state,
        subject=subject,
        category=category,
        without_category=without_category,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/{promise_id}")
def get_promise(promise_id: int, user: EditorialUser, db: DbSession) -> PromiseAdminDetail:
    """Detail with evidence and every verdict version, drafts included."""
    return service.get_detail(db, promise_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_promise(body: PromiseCreate, user: EditorUser, db: DbSession) -> PromiseAdminDetail:
    """New promise as a draft (navrh). It is public only after approval."""
    return service.create(db, user, body.model_dump())


@router.patch("/{promise_id}")
def update_promise(
    promise_id: int, body: PromiseUpdate, user: EditorUser, db: DbSession
) -> PromiseAdminDetail:
    """Change only the sent fields. Changing a filled-in quote or page needs a reason."""
    values = body.model_dump(exclude_unset=True)
    reason = values.pop("reason", None)
    return service.update(db, user, promise_id, values, reason)


@router.post("/{promise_id}/approve")
def approve_promise(promise_id: int, user: EditorUser, db: DbSession) -> PromiseAdminDetail:
    return service.approve(db, user, promise_id)


@router.post("/{promise_id}/reject")
def reject_promise(
    promise_id: int, body: RejectRequest, user: EditorUser, db: DbSession
) -> PromiseAdminDetail:
    """Hide from the public (not a promise, duplicate, ...). The reason is required."""
    return service.reject(db, user, promise_id, body.reason)


@router.post("/{promise_id}/evidence", status_code=status.HTTP_201_CREATED)
def add_evidence(
    promise_id: int, body: EvidenceCreate, user: EditorUser, db: DbSession
) -> PromiseAdminDetail:
    """Attach a quoted passage from a document (see /admin/documents)."""
    return service.add_evidence(db, user, promise_id, body.model_dump())


@router.delete("/{promise_id}/evidence/{evidence_id}")
def delete_evidence(
    promise_id: int,
    evidence_id: int,
    user: EditorUser,
    db: DbSession,
    reason: Annotated[str, Query(min_length=3, max_length=1000, description="Prečo sa maže")],
) -> PromiseAdminDetail:
    return service.delete_evidence(db, user, promise_id, evidence_id, reason)


# --- Comments by the political scientist ---


@router.post("/{promise_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    promise_id: int, body: CommentWrite, user: VerifierUser, db: DbSession
) -> PromiseAdminDetail:
    """A promise may have many comments, all of them are public (role only, no name).

    A comment makes the promise "dovysvetlený", it does not approve the verdict.
    """
    return comment_service.create(db, user, promise_id, body.text)


@router.patch("/{promise_id}/comments/{comment_id}")
def update_comment(
    promise_id: int, comment_id: int, body: CommentWrite, user: VerifierUser, db: DbSession
) -> PromiseAdminDetail:
    """Only the author (or an admin) may change a comment."""
    return comment_service.update(db, user, promise_id, comment_id, body.text)


@router.delete("/{promise_id}/comments/{comment_id}")
def delete_comment(
    promise_id: int, comment_id: int, user: VerifierUser, db: DbSession
) -> PromiseAdminDetail:
    """Only the author (or an admin) may delete a comment."""
    return comment_service.delete(db, user, promise_id, comment_id)
