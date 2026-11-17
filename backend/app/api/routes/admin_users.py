"""User management. Admins only (with 2FA)."""

from fastapi import APIRouter, status

from app.api.deps import AdminUser
from app.core.db import DbSession
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/admin/users", tags=["admin: users"])


@router.get("")
def list_users(admin: AdminUser, db: DbSession) -> list[UserOut]:
    return user_service.list_users(db)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, admin: AdminUser, db: DbSession) -> UserOut:
    """New team member. They set up 2FA themselves after the first login."""
    return user_service.create_user(db, body.email, body.name, body.role, body.password)


@router.patch("/{user_id}")
def update_user(user_id: int, body: UserUpdate, admin: AdminUser, db: DbSession) -> UserOut:
    """Change name, role, active state or reset the password (ends their sessions)."""
    return user_service.update_user(db, admin, user_id, **body.model_dump(exclude_unset=True))
