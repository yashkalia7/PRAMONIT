"""Orchestrates the recompute cascade after anything changes a submission.

Any write that can affect a student's standing — upload, approve, reject,
auto-approve, re-rate — funnels through :func:`refresh_student_progress`. Having
exactly one entry point is what keeps week results, points and streaks from ever
drifting out of agreement with the submissions that produced them.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import current_week_start
from app.models.progress import StudentStreak
from app.services import scoring, streak as streak_service


async def refresh_student_progress(
    session: AsyncSession,
    student_id: uuid.UUID,
    weeks: set[date] | list[date] | None = None,
) -> StudentStreak:
    """Recompute week results, points and the cached streak for one student.

    ``weeks`` narrows the work to the weeks actually affected; pass ``None`` to
    rebuild everything (used by the seeder and by repair scripts).
    """
    if weeks is None:
        target_weeks = await streak_service.weeks_touched_by(session, student_id)
    else:
        target_weeks = sorted(set(weeks))

    for week_start in target_weeks:
        result = await streak_service.recompute_week_result(session, student_id, week_start)
        await scoring.sync_week_points(session, student_id, week_start, result)

    cached = await streak_service.recompute_streak(session, student_id)
    await scoring.award_streak_milestones(
        session, student_id, cached.current_weeks, current_week_start()
    )
    return cached
