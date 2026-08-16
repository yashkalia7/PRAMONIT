"""Student-facing progress: streak and week history."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import DbSession, StudentUser
from app.core.timeutil import current_week_start, label_for_week, recent_week_starts
from app.models.progress import StudentStreak, WeekResult
from app.schemas.progress import StreakOut, WeekHistoryOut, WeekOut
from app.services.scoring import total_points

router = APIRouter(prefix="/me", tags=["me"])


def _week_out(week_start, result: WeekResult | None, current) -> WeekOut:
    return WeekOut(
        week_start=week_start,
        week_label=label_for_week(week_start),
        approved_count=result.approved_count if result else 0,
        pending_count=result.pending_count if result else 0,
        rejected_count=result.rejected_count if result else 0,
        required_count=(
            result.required_count if result else settings.WEEKLY_REQUIRED_SUBMISSIONS
        ),
        met=result.met if result else False,
        finalised=result.finalised if result else False,
        is_current=week_start == current,
    )


@router.get("/streak", response_model=StreakOut)
async def my_streak(session: DbSession, student: StudentUser) -> StreakOut:
    week_start = current_week_start()

    streak = (
        await session.execute(
            select(StudentStreak).where(StudentStreak.student_id == student.id)
        )
    ).scalar_one_or_none()

    this_week = (
        await session.execute(
            select(WeekResult).where(
                WeekResult.student_id == student.id, WeekResult.week_start == week_start
            )
        )
    ).scalar_one_or_none()

    return StreakOut(
        current_weeks=streak.current_weeks if streak else 0,
        longest_weeks=streak.longest_weeks if streak else 0,
        last_met_week=streak.last_met_week if streak else None,
        provisional=streak.provisional if streak else False,
        total_approved=streak.total_approved if streak else 0,
        total_points=await total_points(session, student.id),
        this_week=_week_out(week_start, this_week, week_start),
    )


@router.get("/weeks", response_model=WeekHistoryOut)
async def my_weeks(
    session: DbSession,
    student: StudentUser,
    limit: int = Query(default=12, ge=1, le=104),
) -> WeekHistoryOut:
    current = current_week_start()
    wanted = recent_week_starts(limit, ending=current)

    rows = (
        await session.execute(
            select(WeekResult).where(
                WeekResult.student_id == student.id,
                WeekResult.week_start.in_(wanted),
            )
        )
    ).scalars().all()
    by_week = {row.week_start: row for row in rows}

    # Weeks with no submissions at all have no row; they must still appear in
    # the history strip, as gaps are exactly what the student should see.
    return WeekHistoryOut(
        weeks=[_week_out(week, by_week.get(week), current) for week in wanted]
    )
