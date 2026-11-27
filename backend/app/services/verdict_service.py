"""Verdicts: when they may go public, and verification by a political scientist.

AI verdicts are published right away (team decision 25. 11. 2026). A political
scientist can later verify one, optionally changing its value or reason. That makes
a new version marked "overený politológom"; the old one becomes nahradeny.
A comment alone is not a verification.
"""

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Evidence, Promise, Subject, User, Verdict
from app.models.enums import (
    PUBLIC_VERDICT_VALUES,
    DocumentKind,
    EvidenceRole,
    VerdictState,
    VerdictValue,
)
from app.schemas.common import Page
from app.schemas.verdict import VerdictQueueItem
from app.services import audit
from app.services.comment_service import PUBLIC_ROLE
from app.services.errors import Conflict, Invalid, NotFound

# Only these versions can be verified: the public one, or a draft waiting for review.
CURRENT_STATES = (VerdictState.PUBLIKOVANY, VerdictState.NAVRH)


# --- Rules ------------------------------------------------------------------


def _supporting(evidence: Iterable[Evidence]) -> list[Evidence]:
    return [e for e in evidence if e.role == EvidenceRole.PODKLAD]


def publish_problem(value: VerdictValue, evidence: Iterable[Evidence]) -> str | None:
    """Why an AI verdict can't be published, or None when it can.

    "nesplnene" says that no evidence was found, so it needs none.
    """
    if value not in PUBLIC_VERDICT_VALUES:
        return f"Hodnota '{value.value}' sa nikdy nepublikuje"
    if value != VerdictValue.NESPLNENE and not _supporting(evidence):
        return "Verdikt potrebuje aspoň jeden dôkaz"
    return None


def verify_problem(value: VerdictValue, evidence: Iterable[Evidence]) -> str | None:
    """Why a verdict can't be verified, or None when it can.

    A political scientist vouches only for a published document (law, resolution,
    contract, vote, ...). A news article is just a tip (CONTRIBUTING, point 7).
    """
    if problem := publish_problem(value, evidence):
        return problem
    if value == VerdictValue.NESPLNENE:
        return None
    if not any(e.document.kind != DocumentKind.WEB for e in _supporting(evidence)):
        return (
            "Overenie potrebuje dôkaz z publikovaného dokumentu "
            "(zákon, uznesenie, zmluva, hlasovanie); článok z médií nestačí"
        )
    return None


# --- Reading ----------------------------------------------------------------


def queue(
    db: Session,
    *,
    verified: bool | None = None,
    value: VerdictValue | None = None,
    state: VerdictState | None = None,
    subject: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page[VerdictQueueItem]:
    """Current verdicts (published or draft) for the political scientist, oldest first."""
    stmt = select(Verdict).join(Verdict.promise).where(Verdict.state.in_(CURRENT_STATES))
    if verified is not None:
        reviewed = Verdict.reviewer_role.is_not(None)
        stmt = stmt.where(reviewed if verified else ~reviewed)
    if value:
        stmt = stmt.where(Verdict.value == value)
    if state:
        stmt = stmt.where(Verdict.state == state)
    if subject:
        stmt = stmt.where(Promise.subject.has(Subject.slug == subject))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Verdict.promise).selectinload(Promise.subject))
        .order_by(Verdict.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[VerdictQueueItem.model_validate(v) for v in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Verification -----------------------------------------------------------


def verify(
    db: Session,
    actor: User,
    verdict_id: int,
    reason: str,
    value: VerdictValue | None = None,
    explanation: str | None = None,
) -> Verdict:
    """The political scientist confirms (or corrects) a verdict and it is published."""
    current = db.get(Verdict, verdict_id)
    if current is None:
        raise NotFound("Verdikt sa nenašiel")
    if current.state not in CURRENT_STATES:
        raise Conflict("Overiť sa dá len aktuálny verdikt (publikovaný alebo návrh)")

    new_value = value or current.value
    new_text = (explanation or "").strip() or current.explanation
    changed = new_value != current.value or new_text != current.explanation
    if current.verified and not changed:
        raise Conflict("Verdikt už je overený politológom")

    promise = db.scalar(
        select(Promise)
        .where(Promise.id == current.promise_id)
        .options(selectinload(Promise.evidence).selectinload(Evidence.document))
    )
    if problem := verify_problem(new_value, promise.evidence):
        raise Invalid(problem)

    # The previous public version and any open draft are replaced, never deleted.
    for old in db.scalars(
        select(Verdict).where(Verdict.promise_id == promise.id, Verdict.state.in_(CURRENT_STATES))
    ):
        old.state = VerdictState.NAHRADENY

    latest = db.scalar(select(func.max(Verdict.version)).where(Verdict.promise_id == promise.id))
    verdict = Verdict(
        version=latest + 1,
        value=new_value,
        explanation=new_text,
        state=VerdictState.PUBLIKOVANY,
        # The AI confidence and label stay only when the text is still the AI's.
        confidence=None if changed else current.confidence,
        ai_generated=current.ai_generated and not changed,
        reviewer_role=PUBLIC_ROLE[actor.role],
        review_reason=reason,
        published_at=datetime.now(UTC),
    )
    promise.verdicts.append(verdict)  # keeps the loaded promise in sync
    db.flush()
    audit.record(
        db,
        actor,
        "verify",
        "verdict",
        verdict.id,
        before={"id": current.id, "value": current.value.value, "state": current.state.value},
        after=audit.snapshot(verdict),
        reason=reason,
    )
    db.commit()
    return verdict
