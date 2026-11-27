"""Create the first admin account, with 2FA set up right away.

Usage (in backend/):    python -m app.create_admin admin@example.com "Meno Priezvisko"
In Docker:              docker compose exec backend python -m app.create_admin ...

The password is asked for interactively, so it never ends up in the shell history.
"""

import getpass
import sys

from app.core import security
from app.core.db import SessionLocal
from app.models.enums import UserRole
from app.services import audit, user_service
from app.services.errors import ServiceError


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit('Usage: python -m app.create_admin <email> "<name>"')
    email, name = sys.argv[1], sys.argv[2]

    password = getpass.getpass("Heslo (aspoň 12 znakov): ")
    if len(password) < 12 or password != getpass.getpass("Heslo znova: "):
        sys.exit("Heslo je kratšie ako 12 znakov alebo sa nezhoduje.")

    with SessionLocal() as db:
        try:
            user = user_service.create_user(db, email, name, UserRole.ADMIN, password)
        except ServiceError as exc:
            sys.exit(exc.detail)
        # Admins must use 2FA, so it is enabled immediately.
        user.totp_secret = security.new_totp_secret()
        user.totp_enabled = True
        audit.record(db, None, "enable_2fa", "app_user", user.id, after={"totp_enabled": True})
        db.commit()
        uri = security.totp_uri(user.totp_secret, user.email)

    print(f"Admin {user.email} vytvorený.")
    print("Pridaj si 2FA do aplikácie (Google Authenticator, Aegis, 1Password...):")
    print(f"  kľúč: {user.totp_secret}")
    print(f"  odkaz: {uri}")


if __name__ == "__main__":
    main()
