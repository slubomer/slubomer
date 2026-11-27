"""Shared route dependencies: who is logged in and what they may do.

Usage in a route:
    def route(user: CurrentUser): ...                         any logged-in user
    def route(user: Annotated[User, Depends(require_role(UserRole.OVEROVATEL))]): ...
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import settings
from app.core.db import DbSession
from app.models import User
from app.models.enums import UserRole
from app.services import auth_service
from app.services.errors import Forbidden, Unauthorized


def session_token(request: Request) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def get_current_user(request: Request, db: DbSession) -> User:
    user = auth_service.user_from_token(db, session_token(request))
    if user is None:
        raise Unauthorized("Prihlás sa")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole) -> Callable[[User], User]:
    """Allow only the given roles. Admin is always allowed, but only with 2FA on."""

    def check(user: CurrentUser) -> User:
        if user.role == UserRole.ADMIN:
            if not user.totp_enabled:
                raise Forbidden("Admin musí mať zapnutú 2FA (POST /api/v1/auth/2fa/setup)")
            return user
        if user.role not in roles:
            raise Forbidden("Na túto akciu nemáš oprávnenie")
        return user

    return check


AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]

# Editorial team: the verifier may read editorial data, only the editor changes it.
EditorialUser = Annotated[User, Depends(require_role(UserRole.REDAKTOR, UserRole.OVEROVATEL))]
EditorUser = Annotated[User, Depends(require_role(UserRole.REDAKTOR))]
