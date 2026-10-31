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


settings = Settings()
