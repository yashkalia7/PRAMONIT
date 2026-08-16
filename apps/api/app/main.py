"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import settings
from app.core.timeutil import current_week_start, label_for_week
from app.db.session import backend_name, dispose_engine, ping, using_fallback_db
from app.routers import auth, coach, drills, leaderboard, me, media, submissions

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s | %(message)s"
)
log = logging.getLogger("pramonit")

scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global scheduler

    if using_fallback_db():
        # No Postgres configured: create the schema directly so the whole app is
        # runnable and testable with nothing installed. With Postgres, Alembic
        # owns the schema and this is deliberately skipped.
        from app.db.init_db import create_all

        await create_all()
        log.warning("running on the SQLite fallback — schema created via create_all()")

    if settings.ENABLE_SWEEPER:
        scheduler = AsyncIOScheduler(timezone="UTC")
        from app.services.sweeper import sweep_once

        scheduler.add_job(
            sweep_once,
            "interval",
            minutes=settings.SWEEPER_INTERVAL_MINUTES,
            id="auto_approve_sweep",
            # If the process was down over several intervals, run once on
            # recovery rather than firing every missed slot at boot.
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
        scheduler.start()
        log.info(
            "auto-approve sweeper active: every %d min, threshold %d h",
            settings.SWEEPER_INTERVAL_MINUTES,
            settings.AUTO_APPROVE_AFTER_HOURS,
        )

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version=__version__,
        description=(
            "Training-video accountability for Pramonit Football Academy. "
            "Students upload ball-mastery drills, coaches review them, and week "
            "streaks plus leaderboards surface who is actually putting the work in."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Range", "Accept-Ranges"],
    )

    prefix = settings.API_PREFIX
    app.include_router(auth.router, prefix=prefix)
    app.include_router(auth.public_router, prefix=prefix)
    app.include_router(drills.router, prefix=prefix)
    app.include_router(submissions.router, prefix=prefix)
    app.include_router(me.router, prefix=prefix)
    app.include_router(leaderboard.router, prefix=prefix)
    app.include_router(coach.router, prefix=prefix)

    if settings.STORAGE_BACKEND == "local":
        app.include_router(media.router, prefix=prefix)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, object]:
        week = current_week_start()
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": __version__,
            "env": settings.ENV,
            "database": {
                "backend": backend_name(),
                "reachable": await ping(),
                "fallback_mode": using_fallback_db(),
            },
            "storage": settings.STORAGE_BACKEND,
            "timezone": settings.APP_TIMEZONE,
            "current_week": {"start": week.isoformat(), "label": label_for_week(week)},
            "rules": {
                "weekly_required_submissions": settings.WEEKLY_REQUIRED_SUBMISSIONS,
                "auto_approve_after_hours": settings.AUTO_APPROVE_AFTER_HOURS,
            },
        }

    @app.post("/admin/sweep", tags=["meta"])
    async def trigger_sweep() -> dict[str, object]:
        """Run the auto-approve sweep immediately.

        Non-production only. Waiting 72 real hours to check the safety valve
        works is not a testing strategy.
        """
        if settings.ENV == "prod":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not available in production"
            )
        from app.services.sweeper import sweep_once

        report = await sweep_once()
        return {
            "approved": report.approved,
            "students_touched": report.students_touched,
        }

    return app


app = create_app()
