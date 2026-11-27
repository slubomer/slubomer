"""App settings, read from environment variables or the .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads .env from the repo root or the current folder (the later file wins).
    # Empty values (e.g. "DEBUG=") are ignored, so the defaults below apply.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_ignore_empty=True, extra="ignore"
    )

    # Format: postgresql+psycopg://user:password@host:5432/dbname
    # The real value comes from .env, the default only lets the app start without one.
    database_url: str = "postgresql+psycopg://localhost:5432/slubomer"
    debug: bool = False

    # --- Login ---
    session_cookie_name: str = "slubomer_session"
    session_ttl_hours: int = 12
    # Session cookie only over HTTPS. Secure by default, so production can't forget it;
    # set COOKIE_SECURE=false for http://localhost (docker-compose does it already).
    cookie_secure: bool = True
    # Failed logins in a row before the account is locked, and for how long.
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # Comma-separated origins allowed to call the API from a browser,
    # e.g. "http://localhost:3000,https://slubomer.sk". Empty = no CORS.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
