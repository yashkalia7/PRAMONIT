"""The 72-hour auto-approve sweeper.

Counting is gated on coach approval, which is the right call for integrity but
creates a dependency no student can control: a coach who travels for a week
would silently break every streak in their batch. The sweeper is the safety
valve. Anything unreviewed after ``AUTO_APPROVE_AFTER_HOURS`` is approved and
tagged ``auto_approved`` so the origin of the credit stays visible, and the coach
can still reject it afterwards.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.timeutil import now_utc
from app.models.enums import SubmissionStatus
from app.models.submission import Submission
from app.services.progress import refresh_student_progress

log = logging.getLogger("pramonit.sweeper")


@dataclass(slots=True)
class SweepReport:
    approved: int = 0
    students_touched: int = 0
    submission_ids: list[uuid.UUID] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.approved > 0


async def run_auto_approve(session: AsyncSession, *, commit: bool = True) -> SweepReport:
    cutoff = now_utc() - timedelta(hours=settings.AUTO_APPROVE_AFTER_HOURS)

    stale = (
        await session.execute(
            select(Submission).where(
                Submission.status == SubmissionStatus.pending,
                Submission.submitted_at < cutoff,
            )
        )
    ).scalars().all()

    if not stale:
        return SweepReport()

    touched: dict[uuid.UUID, set[date]] = defaultdict(set)
    now = now_utc()

    for submission in stale:
        submission.status = SubmissionStatus.approved
        submission.auto_approved = True
        submission.reviewed_at = now
        submission.reviewed_by = None
        touched[submission.student_id].add(submission.counts_for_week)

    await session.flush()

    for student_id, weeks in touched.items():
        await refresh_student_progress(session, student_id, weeks)

    if commit:
        await session.commit()

    log.info(
        "auto-approved %d submission(s) older than %dh across %d student(s)",
        len(stale),
        settings.AUTO_APPROVE_AFTER_HOURS,
        len(touched),
    )
    return SweepReport(
        approved=len(stale),
        students_touched=len(touched),
        submission_ids=[s.id for s in stale],
    )


async def sweep_once() -> SweepReport:
    """Entry point for the scheduler — owns its own session."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        try:
            return await run_auto_approve(session)
        except Exception:  # pragma: no cover - defensive; a crash must not kill the job
            await session.rollback()
            log.exception("auto-approve sweep failed")
            return SweepReport()
