"""Aggregated numbers for the overview charts. Counting happens in SQL."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Promise, Subject, Verdict
from app.models.enums import PromiseState, VerdictState
from app.schemas.catalog import SubjectOut
from app.schemas.stats import OverviewStats, SubjectStats, VerdictCounts

_PUBLIC_PROMISE = Promise.state == PromiseState.SCHVALENY
_PUBLISHED_VERDICT = Verdict.state == VerdictState.PUBLIKOVANY


def _rated(counts: VerdictCounts) -> int:
    """Number of promises that have a published verdict."""
    return counts.splneny + counts.nesplneny + counts.v_procese


def overview(db: Session) -> OverviewStats:
    total = db.scalar(select(func.count(Promise.id)).where(_PUBLIC_PROMISE)) or 0
    rows = db.execute(
        select(Verdict.value, func.count())
        .join(Promise, Promise.id == Verdict.promise_id)
        .where(_PUBLIC_PROMISE, _PUBLISHED_VERDICT)
        .group_by(Verdict.value)
    ).all()
    counts = VerdictCounts(**{v.value: n for v, n in rows})
    return OverviewStats(total=total, by_verdict=counts, unrated=total - _rated(counts))


def by_subject(db: Session) -> list[SubjectStats]:
    subjects = db.scalars(select(Subject).order_by(Subject.name)).all()

    totals = dict(
        db.execute(
            select(Promise.subject_id, func.count())
            .where(_PUBLIC_PROMISE)
            .group_by(Promise.subject_id)
        ).all()
    )

    counts: dict[int, dict[str, int]] = {}
    rows = db.execute(
        select(Promise.subject_id, Verdict.value, func.count())
        .join(Verdict, Verdict.promise_id == Promise.id)
        .where(_PUBLIC_PROMISE, _PUBLISHED_VERDICT)
        .group_by(Promise.subject_id, Verdict.value)
    ).all()
    for subject_id, value, n in rows:
        counts.setdefault(subject_id, {})[value.value] = n

    result = []
    for s in subjects:
        subject_counts = VerdictCounts(**counts.get(s.id, {}))
        total = totals.get(s.id, 0)
        result.append(
            SubjectStats(
                subject=SubjectOut.model_validate(s),
                total=total,
                by_verdict=subject_counts,
                unrated=total - _rated(subject_counts),
            )
        )
    return result
