"""Schema bootstrap.

Two paths, deliberately kept separate:

* **Postgres** — Alembic owns the schema. Migrations are versioned and
  reviewable, which is what you want for anything holding real data.
* **SQLite fallback** — ``create_all`` builds the tables directly. There is no
  history worth migrating in a throwaway development database, and requiring a
  migration step would defeat the point of the zero-setup mode.
"""

from __future__ import annotations

import asyncio
import logging

from app.db.session import engine
from app.models import Base

log = logging.getLogger("pramonit.db")


async def create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def reset() -> None:
    await drop_all()
    await create_all()


if __name__ == "__main__":  # pragma: no cover - operator entry point
    import sys

    action = sys.argv[1] if len(sys.argv) > 1 else "create"
    runner = {"create": create_all, "drop": drop_all, "reset": reset}[action]
    asyncio.run(runner())
    log.info("schema %s complete", action)
    print(f"schema {action} complete")
