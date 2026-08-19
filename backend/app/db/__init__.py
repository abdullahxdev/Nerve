"""
app/db/__init__.py
──────────────────
Database engine + session factory.

Key concepts:
  - `create_async_engine`: SQLAlchemy's async engine. Uses asyncpg under the hood.
    Unlike the sync engine, it never blocks the event loop while waiting for Postgres.

  - `AsyncSession`: An async-compatible session. All DB operations must be awaited.

  - `AsyncSessionLocal`: A factory that creates new session instances.
    We use it inside a FastAPI dependency (get_db) to scope one session per request.

  - `Base`: Declarative base class. All SQLAlchemy models inherit from this.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# echo=True prints every SQL statement to stdout — useful while learning/debugging.
# Turn it off in production (app_debug=False).
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=10,         # max persistent connections in the pool
    max_overflow=20,      # extra connections allowed when pool is full
)


# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # don't expire objects after commit (avoids lazy-load errors)
)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this class."""
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    Yields a database session scoped to a single HTTP request.

    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...

    The `async with` block ensures the session is always closed
    (and rolled back on error) even if an exception is raised.
    """
    async with AsyncSessionLocal() as session:
        yield session
