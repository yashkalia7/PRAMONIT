"""Leaderboard points.

The ledger is append-only, and reconciliation works by *convergence* rather than
by applying deltas at each event: for a given student-week we compute what the
totals per reason ought to be, compare against what the ledger already says, and
write a single correcting row per reason that disagrees.

That choice buys three things a naive "+10 on approve, -10 on reject" scheme
does not:

* **Idempotence.** Running it twice changes nothing the second time, so a retried
  request or a double-fired sweeper cannot inflate anyone's score.
* **Self-healing.** If a bug ever miscounts, the next recompute silently repairs
  the total instead of preserving the error forever.
* **Auditability.** Every row still carries its reason, so a disputed ranking can
  be explained line by line to a parent.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import PointsReason, SubmissionStatus
from app.models.progress import PointsLedger, WeekResult
from app.models.submission import Submission

POINTS_PER_APPROVED = 10
POINTS_WEEKLY_GOAL = 25
POINTS_PER_EXTRA = 5
MAX_EXTRA_AWARDED = 5          # beyond this, volume stops paying
POINTS_HIGH_RATING = 5
HIGH_RATING_THRESHOLD = 4
POINTS_STREAK_MILESTONE = 50
STREAK_MILESTONES = (4, 8, 12, 26, 52)

# Milestones are lifetime achievements, not weekly ones, so they are excluded
# from the per-week convergence and handled separately.
WEEKLY_REASONS = (
    PointsReason.approved_submission,
    PointsReason.weekly_goal_met,
    PointsReason.extra_submission,
    PointsReason.high_rating,
)


async def _target_breakdown(
    session: AsyncSession, student_id: uuid.UUID, week_start: date, result: WeekResult
) -> dict[PointsReason, int]:
    required = settings.WEEKLY_REQUIRED_SUBMISSIONS
    approved = result.approved_count

    high_rated = (
        await session.execute(
            select(func.count())
            .select_from(Submission)
            .where(
                Submission.student_id == student_id,
                Submission.counts_for_week == week_start,
                Submission.status == SubmissionStatus.approved,
                Submission.coach_rating >= HIGH_RATING_THRESHOLD,
            )
        )
    ).scalar_one()

    extra = min(max(approved - required, 0), MAX_EXTRA_AWARDED)

    return {
        PointsReason.approved_submission: approved * POINTS_PER_APPROVED,
        PointsReason.weekly_goal_met: POINTS_WEEKLY_GOAL if result.met else 0,
        PointsReason.extra_submission: extra * POINTS_PER_EXTRA,
        PointsReason.high_rating: high_rated * POINTS_HIGH_RATING,
    }


async def _ledger_totals(
    session: AsyncSession, student_id: uuid.UUID, week_start: date
) -> dict[PointsReason, int]:
    rows = (
        await session.execute(
            select(PointsLedger.reason, func.coalesce(func.sum(PointsLedger.points), 0))
            .where(
                PointsLedger.student_id == student_id,
                PointsLedger.week_start == week_start,
                PointsLedger.reason.in_(WEEKLY_REASONS),
            )
            .group_by(PointsLedger.reason)
        )
    ).all()
    return {reason: int(total) for reason, total in rows}


async def sync_week_points(
    session: AsyncSession, student_id: uuid.UUID, week_start: date, result: WeekResult
) -> int:
    """Converge the ledger for one student-week. Returns the net adjustment."""
    target = await _target_breakdown(session, student_id, week_start, result)
    actual = await _ledger_totals(session, student_id, week_start)

    net = 0
    for reason, want in target.items():
        have = actual.get(reason, 0)
        delta = want - have
        if delta == 0:
            continue
        session.add(
            PointsLedger(
                student_id=student_id,
                reason=reason,
                points=delta,
                week_start=week_start,
                detail="adjustment" if have else None,
            )
        )
        net += delta

    if net:
        await session.flush()
    return net


async def award_streak_milestones(
    session: AsyncSession, student_id: uuid.UUID, current_weeks: int, week_start: date
) -> int:
    """One-off bonuses at 4/8/12/26/52 weeks, never awarded twice."""
    earned = [m for m in STREAK_MILESTONES if current_weeks >= m]
    if not earned:
        return 0

    already = set(
        (
            await session.execute(
                select(PointsLedger.detail).where(
                    PointsLedger.student_id == student_id,
                    PointsLedger.reason == PointsReason.streak_milestone,
                )
            )
        ).scalars().all()
    )

    total = 0
    for milestone in earned:
        key = f"streak-{milestone}"
        if key in already:
            continue
        session.add(
            PointsLedger(
                student_id=student_id,
                reason=PointsReason.streak_milestone,
                points=POINTS_STREAK_MILESTONE,
                week_start=week_start,
                detail=key,
            )
        )
        total += POINTS_STREAK_MILESTONE

    if total:
        await session.flush()
    return total


async def total_points(session: AsyncSession, student_id: uuid.UUID) -> int:
    return int(
        (
            await session.execute(
                select(func.coalesce(func.sum(PointsLedger.points), 0)).where(
                    PointsLedger.student_id == student_id
                )
            )
        ).scalar_one()
    )
