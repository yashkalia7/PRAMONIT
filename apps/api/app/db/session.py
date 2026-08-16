"""Database engine and session management.

The app runs against two very different backends without changing a line of
model or route code:

* **Supabase Postgres** when ``DATABASE_URL`` is set — the real deployment.
* **SQLite** when it is not — so the entire API, test suite and browser E2E run
  on a fresh machine with no database to install, no account to create and no
  credential to hand over.

Every model is written with dialect-portable column types so these two paths
exercise genuinely the same code.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

log = logging.getLogger("pramonit.db")

SQLITE_FILE = Path(__file__).resolve().parents[2] / "pramonit.dev.db"
SQLITE_DSN = f"sqlite+aiosqlite:///{SQLITE_FILE.as_posix()}"


def resolve_engine_config() -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Return ``(dsn, connect_args, engine_kwargs)`` for the active backend."""
    if settings.db_configured:
        dsn, connect_args = settings.runtime_db()
        engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
        if "statement_cache_size" in connect_args:
            # Behind pgbouncer: it already pools, so client-side pooling only
            # adds stale connections.
            engine_kwargs["poolclass"] = NullPool
            engine_kwargs.pop("pool_pre_ping", None)
        return dsn, connect_args, engine_kwargs

    log.warning(
        "DATABASE_URL is not configured — falling back to SQLite at %s. "
        "This is fine for development and testing; set DATABASE_URL to your "
        "Supabase connection string for production.",
        SQLITE_FILE.name,
    )
    return SQLITE_DSN, {"check_same_thread": False}, {"poolclass": NullPool}


def build_engine(dsn: str | None = None, **overrides: Any) -> AsyncEngine:
    resolved_dsn, connect_args, engine_kwargs = resolve_engine_config()
    engine = create_async_engine(
        dsn or resolved_dsn,
        echo=False,
        future=True,
        connect_args=connect_args if dsn is None else overrides.pop("connect_args", {}),
        **{**engine_kwargs, **overrides},
    )
    _install_sqlite_pragmas(engine)
    return engine


def _install_sqlite_pragmas(engine: AsyncEngine) -> None:
    """SQLite ignores foreign keys unless asked, and defaults to a lock-happy
    journal. Neither default is acceptable for a test backend that is meant to
    behave like Postgres."""
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


engine: AsyncEngine = build_engine()

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def using_fallback_db() -> bool:
    return not settings.db_configured


def backend_name() -> str:
    return "postgresql" if settings.db_configured else "sqlite"


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session that always closes."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def ping() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover - diagnostics only
        log.error("database ping failed: %s", exc)
        return False


async def dispose_engine() -> None:
    await engine.dispose()
