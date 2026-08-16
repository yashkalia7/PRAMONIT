"""Leaderboard queries.

Three scopes and two windows, plus one rule that matters more than any of them:
the viewer's own row is always returned, even when they sit 87th. A board a
student cannot find themselves on is a board they stop opening.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import current_week_start
from app.models.enums import LeaderboardScope, LeaderboardWindow, RosterStatus, UserRole
from app.models.progress import PointsLedger, StudentStreak
from app.models.user import StudentProfile, User


@dataclass(slots=True)
class LeaderboardRow:
    rank: int
    student_id: uuid.UUID
    full_name: str
    batch_name: str | None
    points: int
    current_weeks: int
    approved_total: int
    is_viewer: bool = False


@dataclass(slots=True)
class LeaderboardPage:
    scope: LeaderboardScope
    window: LeaderboardWindow
    week_start: date | None
    rows: list[LeaderboardRow]
    viewer_row: LeaderboardRow | None
    total_students: int


async def _viewer_profile(
    session: AsyncSession, viewer_id: uuid.UUID | None
) -> StudentProfile | None:
    if viewer_id is None:
        return None
    return (
        await session.execute(
            select(StudentProfile).where(StudentProfile.user_id == viewer_id)
        )
    ).scalar_one_or_none()


async def build_leaderboard(
    session: AsyncSession,
    *,
    scope: LeaderboardScope,
    window: LeaderboardWindow,
    viewer_id: uuid.UUID | None = None,
    coach_id: uuid.UUID | None = None,
    batch_name: str | None = None,
    limit: int = 50,
) -> LeaderboardPage:
    week_start = current_week_start() if window == LeaderboardWindow.week else None

    viewer_profile = await _viewer_profile(session, viewer_id)
    if viewer_profile is not None:
        coach_id = coach_id or viewer_profile.coach_id
        batch_name = batch_name or viewer_profile.batch_name

    # LEFT JOIN, not INNER: a student with zero points still belongs on the
    # board. Filtering the ledger inside the ON clause rather than the WHERE
    # clause is what preserves those zero rows for the weekly window.
    ledger_join = PointsLedger.student_id == User.id
    if week_start is not None:
        ledger_join = ledger_join & (PointsLedger.week_start == week_start)

    query = (
        select(
            User.id,
            User.full_name,
            StudentProfile.batch_name,
            func.coalesce(func.sum(PointsLedger.points), 0).label("points"),
            func.coalesce(func.max(StudentStreak.current_weeks), 0).label("current_weeks"),
            func.coalesce(func.max(StudentStreak.total_approved), 0).label("approved_total"),
        )
        .select_from(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .outerjoin(PointsLedger, ledger_join)
        .outerjoin(StudentStreak, StudentStreak.student_id == User.id)
        .where(
            User.role == UserRole.student,
            User.is_active.is_(True),
            StudentProfile.roster_status == RosterStatus.active,
        )
        .group_by(User.id, User.full_name, StudentProfile.batch_name)
        .order_by(
            func.coalesce(func.sum(PointsLedger.points), 0).desc(),
            func.coalesce(func.max(StudentStreak.current_weeks), 0).desc(),
            User.full_name.asc(),
        )
    )

    if scope == LeaderboardScope.batch:
        # Batch names are free text and shared across coaches by design — "Powai
        # batch" is a place and a time slot, so students who train together rank
        # together regardless of which coach signed them up.
        query = query.where(StudentProfile.batch_name == batch_name)
    elif scope == LeaderboardScope.coach:
        query = query.where(StudentProfile.coach_id == coach_id)

    rows = (await session.execute(query)).all()

    ranked = [
        LeaderboardRow(
            rank=index,
            student_id=row.id,
            full_name=row.full_name,
            batch_name=row.batch_name,
            points=int(row.points),
            current_weeks=int(row.current_weeks),
            approved_total=int(row.approved_total),
            is_viewer=row.id == viewer_id,
        )
        for index, row in enumerate(rows, start=1)
    ]

    viewer_row = next((r for r in ranked if r.is_viewer), None)
    top = ranked[:limit]
    # Pin the viewer beneath the cut when they did not make it.
    if viewer_row and viewer_row not in top:
        top = [*top, viewer_row]

    return LeaderboardPage(
        scope=scope,
        window=window,
        week_start=week_start,
        rows=top,
        viewer_row=viewer_row,
        total_students=len(ranked),
    )
