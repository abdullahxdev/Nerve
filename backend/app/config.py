from __future__ import annotations  # enables X | Y union syntax on Python 3.9

"""
app/config.py
─────────────
Central settings management using Pydantic v2's BaseSettings.

Why Pydantic settings?
  - Reads values from environment variables (or .env file) automatically.
  - Validates types at startup — if DATABASE_URL is missing, the app crashes
    immediately with a clear error instead of silently failing later.
  - One single `settings` object is imported everywhere — no scattered os.getenv() calls.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "Nerve"
    app_env: str = "development"
    app_debug: bool = True
    secret_key: str

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str  # e.g. postgresql+asyncpg://user:pass@host:port/db

    # ── Webhook ───────────────────────────────────────────────────────────────
    nerve_webhook_secret: str

    # ── Pydantic config ───────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",          # reads from .env in CWD
        env_file_encoding="utf-8",
        case_sensitive=False,     # DATABASE_URL == database_url
    )


# ── Singleton ─────────────────────────────────────────────────────────────────
# Import this object everywhere: `from app.config import settings`
settings = Settings()
