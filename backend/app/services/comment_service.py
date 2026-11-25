"""Political scientists' comments on promises.

A promise may have many comments, all of them are public. Only the author
(or an admin) may change or delete a comment.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Promise, PromiseComment, User
from app.models.enums import UserRole
from app.schemas.admin import PromiseAdminDetail
from app.services import audit, promise_admin_service
from app.services.errors import Forbidden, NotFound

# What the public web shows instead of the author's name (GDPR).
PUBLIC_ROLE = {
    UserRole.OVEROVATEL: "politológ",
    UserRole.ADMIN: "redakcia",
}


def _promise(db: Session, promise_id: int) -> Promise:
    promise = db.get(Promise, promise_id)
    if promise is None:
        raise NotFound("Sľub sa nenašiel")
    return promise


def _own_comment(db: Session, actor: User, promise_id: int, comment_id: int) -> PromiseComment:
    """The comment, if it belongs to the promise and the actor may change it."""
    comment = db.get(PromiseComment, comment_id)
    if comment is None or comment.promise_id != promise_id:
        raise NotFound("Komentár sa nenašiel")
    if actor.role != UserRole.ADMIN and comment.author_id != actor.id:
        raise Forbidden("Upraviť alebo zmazať môžeš len svoj komentár")
    return comment


def create(db: Session, actor: User, promise_id: int, text: str) -> PromiseAdminDetail:
    promise = _promise(db, promise_id)
    comment = PromiseComment(
        promise=promise, author_id=actor.id, author_role=PUBLIC_ROLE[actor.role], text=text
    )
    db.add(comment)
    db.flush()  # assigns comment.id for the audit entry
    audit.record(db, actor, "create", "promise_comment", comment.id, after=audit.snapshot(comment))
    db.commit()
    return promise_admin_service.get_detail(db, promise_id)


def update(
    db: Session, actor: User, promise_id: int, comment_id: int, text: str
) -> PromiseAdminDetail:
    comment = _own_comment(db, actor, promise_id, comment_id)
    if comment.text != text:
        audit.apply_changes(db, actor, comment, "promise_comment", {"text": text})
        comment.updated_at = datetime.now(UTC)
        db.commit()
    return promise_admin_service.get_detail(db, promise_id)


def delete(db: Session, actor: User, promise_id: int, comment_id: int) -> PromiseAdminDetail:
    comment = _own_comment(db, actor, promise_id, comment_id)
    # The whole row goes to the log, so the comment can be restored if needed.
    before = audit.snapshot(comment)
    audit.record(db, actor, "delete", "promise_comment", comment.id, before=before)
    db.delete(comment)
    db.commit()
    return promise_admin_service.get_detail(db, promise_id)
