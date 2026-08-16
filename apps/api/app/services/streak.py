"""Week results and streak computation.

The club rule is deceptively simple — "two videos a week" — but the coach
approval gate makes the edges genuinely subtle:

* A video credits the week it was **uploaded** in, not the week it was approved
  in, so a slow review never moves a student's work between weeks.
* Because of that, a finished week can still be *undecided*: it ended with only
  one approved video but two more awaiting review. Such a week must neither
  extend nor break the streak until its last pending video resolves — which the
  72-hour sweeper guarantees will happen.

Those two rules are why ``WeekResult.finalised`` and ``StudentStreak.provisional``
exist. Everything else here is bookkeeping.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.timeutil import (
    current_week_start,
    shift_weeks,
    week_has_ended,
)
from app.models.enums import SubmissionStatus
from app.models.progress import StudentStreak, WeekResult
from app.models.submission import Submission


@dataclass(slots=True)
class StreakState:
    current_weeks: int
    longest_weeks: int
    last_met_week: date | None
    provisional: bool
    total_approved: int


async def recompute_week_result(
    session: AsyncSession, student_id: uuid.UUID, week_start: date
) -> WeekResult:
    """Recount one student-week from its submissions and upsert the row."""
    rows = (
        await session.execute(
            select(Submission.status, func.count())
            .where(
                Submission.student_id == student_id,
                Submission.counts_for_week == week_start,
            )
            .group_by(Submission.status)
        )
    ).all()

    counts = {status: count for status, count in rows}
    approved = counts.get(SubmissionStatus.approved, 0)
    pending = counts.get(SubmissionStatus.pending, 0)
    rejected = counts.get(SubmissionStatus.rejected, 0)
    required = settings.WEEKLY_REQUIRED_SUBMISSIONS

    result = (
        await session.execute(
            select(WeekResult).where(
                WeekResult.student_id == student_id,
                WeekResult.week_start == week_start,
            )
        )
    ).scalar_one_or_none()

    if result is None:
        result = WeekResult(student_id=student_id, week_start=week_start)
        session.add(result)

    result.approved_count = approved
    result.pending_count = pending
    result.rejected_count = rejected
    result.required_count = required
    result.met = approved >= required
    # A week is settled only once it has ended AND nothing is still awaiting a
    # coach. Pending work keeps the door open.
    result.finalised = week_has_ended(week_start) and pending == 0

    await session.flush()
    return result


async def load_week_results(
    session: AsyncSession, student_id: uuid.UUID
) -> dict[date, WeekResult]:
    rows = (
        await session.execute(
            select(WeekResult)
            .where(WeekResult.student_id == student_id)
            .order_by(WeekResult.week_start)
        )
    ).scalars().all()
    return {row.week_start: row for row in rows}


def compute_streak_state(
    results: dict[date, WeekResult], *, today_week: date | None = None
) -> StreakState:
    """Pure function — the algorithm, with no database in sight, so the tests
    can hammer every boundary case cheaply."""
    current_week = today_week or current_week_start()

    current = 0
    provisional = False
    cursor = current_week

    while True:
        result = results.get(cursor)

        if not week_has_ended(cursor):
            # The week in progress can only ever help. Falling short of the
            # quota mid-week is normal and must not break anything.
            if result and result.met:
                current += 1
            cursor = shift_weeks(cursor, -1)
            continue

        if result and result.met:
            current += 1
            cursor = shift_weeks(cursor, -1)
            continue

        # Ended and short of the quota. If videos are still queued for review
        # the week may yet be rescued, so the streak is held rather than cut.
        if result and result.pending_count > 0:
            provisional = True
        break

    longest = 0
    run = 0
    for week in sorted(results):
        if results[week].met:
            run += 1
            longest = max(longest, run)
        elif week_has_ended(week):
            run = 0
    longest = max(longest, current)

    met_weeks = [w for w, r in results.items() if r.met]
    total_approved = sum(r.approved_count for r in results.values())

    return StreakState(
        current_weeks=current,
        longest_weeks=longest,
        last_met_week=max(met_weeks) if met_weeks else None,
        provisional=provisional,
        total_approved=total_approved,
    )


async def recompute_streak(session: AsyncSession, student_id: uuid.UUID) -> StudentStreak:
    results = await load_week_results(session, student_id)
    state = compute_streak_state(results)

    streak = (
        await session.execute(
            select(StudentStreak).where(StudentStreak.student_id == student_id)
        )
    ).scalar_one_or_none()

    if streak is None:
        streak = StudentStreak(student_id=student_id)
        session.add(streak)

    streak.current_weeks = state.current_weeks
    streak.longest_weeks = max(state.longest_weeks, streak.longest_weeks or 0)
    streak.last_met_week = state.last_met_week
    streak.provisional = state.provisional
    streak.total_approved = state.total_approved

    await session.flush()
    return streak


async def weeks_touched_by(session: AsyncSession, student_id: uuid.UUID) -> list[date]:
    rows = (
        await session.execute(
            select(Submission.counts_for_week)
            .where(Submission.student_id == student_id)
            .distinct()
        )
    ).scalars().all()
    return sorted(rows)
