"""Coach dashboard: roster management and batch compliance."""

from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import CoachUser, DbSession
from app.core.timeutil import current_week_start, ensure_utc, label_for_week, now_utc
from app.models.enums import RosterStatus, SubmissionStatus, UserRole
from app.models.progress import PointsLedger, StudentStreak, WeekResult
from app.models.submission import Submission
from app.models.user import StudentProfile, User
from app.schemas.progress import (
    BatchStatOut,
    CoachStatsOut,
    RosterEntryOut,
    RosterOut,
    RosterUpdateRequest,
)

router = APIRouter(prefix="/coach", tags=["coach"])


async def _roster_rows(session, coach_id: uuid.UUID) -> list[RosterEntryOut]:
    week_start = current_week_start()
    required = settings.WEEKLY_REQUIRED_SUBMISSIONS

    students = (
        await session.execute(
            select(User, StudentProfile)
            .join(StudentProfile, StudentProfile.user_id == User.id)
            .where(
                StudentProfile.coach_id == coach_id,
                StudentProfile.roster_status == RosterStatus.active,
                User.role == UserRole.student,
            )
            .order_by(StudentProfile.batch_name, User.full_name)
        )
    ).all()

    if not students:
        return []

    ids = [user.id for user, _ in students]

    streaks = dict(
        (
            await session.execute(
                select(StudentStreak.student_id, StudentStreak).where(
                    StudentStreak.student_id.in_(ids)
                )
            )
        ).all()
    )
    weeks = dict(
        (
            await session.execute(
                select(WeekResult.student_id, WeekResult).where(
                    WeekResult.student_id.in_(ids), WeekResult.week_start == week_start
                )
            )
        ).all()
    )
    points = dict(
        (
            await session.execute(
                select(PointsLedger.student_id, func.coalesce(func.sum(PointsLedger.points), 0))
                .where(PointsLedger.student_id.in_(ids))
                .group_by(PointsLedger.student_id)
            )
        ).all()
    )

    entries: list[RosterEntryOut] = []
    for user, profile in students:
        streak = streaks.get(user.id)
        week = weeks.get(user.id)
        approved = week.approved_count if week else 0
        pending = week.pending_count if week else 0
        entries.append(
            RosterEntryOut(
                student_id=user.id,
                full_name=user.full_name,
                email=user.email,
                batch_name=profile.batch_name,
                course=profile.course,
                jersey_number=profile.jersey_number,
                preferred_position=profile.preferred_position,
                current_weeks=streak.current_weeks if streak else 0,
                approved_total=streak.total_approved if streak else 0,
                points=int(points.get(user.id, 0)),
                this_week_approved=approved,
                this_week_pending=pending,
                required_count=required,
                # Counts pending too: a student who has uploaded enough and is
                # merely waiting on this coach is not the one to chase.
                at_risk=(approved + pending) < required,
                joined_at=profile.joined_at,
            )
        )
    return entries


@router.get("/roster", response_model=RosterOut)
async def roster(session: DbSession, coach: CoachUser) -> RosterOut:
    entries = await _roster_rows(session, coach.id)
    batches = sorted({e.batch_name for e in entries if e.batch_name})
    return RosterOut(batches=batches, students=entries)


@router.patch("/roster/{student_id}", response_model=RosterEntryOut)
async def update_roster_entry(
    student_id: uuid.UUID,
    payload: RosterUpdateRequest,
    session: DbSession,
    coach: CoachUser,
) -> RosterEntryOut:
    """Reassign a student to another coach, correct their batch, or remove them.

    This is the escape hatch for the signup flow: students choose their own coach
    from a dropdown, so a wrong pick has to be fixable in one click.
    """
    profile = (
        await session.execute(
            select(StudentProfile).where(StudentProfile.user_id == student_id)
        )
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if profile.coach_id != coach.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="That student is not on your roster"
        )

    if payload.remove:
        profile.roster_status = RosterStatus.removed
    if payload.batch_name is not None:
        profile.batch_name = payload.batch_name
    if payload.coach_id is not None:
        target = (
            await session.execute(
                select(User).where(User.id == payload.coach_id, User.role == UserRole.coach)
            )
        ).scalar_one_or_none()
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Target coach does not exist"
            )
        profile.coach_id = target.id
        # Move the student's open work with them, so the receiving coach can
        # actually action it and the old coach's queue does not keep it.
        await session.execute(
            Submission.__table__.update()
            .where(
                Submission.student_id == student_id,
                Submission.status == SubmissionStatus.pending,
            )
            .values(coach_id=target.id)
        )

    await session.commit()

    entries = await _roster_rows(session, coach.id)
    for entry in entries:
        if entry.student_id == student_id:
            return entry

    # Removed or reassigned away — return a minimal echo rather than 404, since
    # the operation itself succeeded.
    return RosterEntryOut(
        student_id=student_id,
        full_name="",
        email="",
        batch_name=profile.batch_name,
        required_count=settings.WEEKLY_REQUIRED_SUBMISSIONS,
    )


@router.get("/stats", response_model=CoachStatsOut)
async def stats(session: DbSession, coach: CoachUser) -> CoachStatsOut:
    week_start = current_week_start()
    entries = await _roster_rows(session, coach.id)

    pending_total = (
        await session.execute(
            select(func.count()).select_from(Submission).where(
                Submission.coach_id == coach.id,
                Submission.status == SubmissionStatus.pending,
            )
        )
    ).scalar_one()

    oldest = (
        await session.execute(
            select(func.min(Submission.submitted_at)).where(
                Submission.coach_id == coach.id,
                Submission.status == SubmissionStatus.pending,
            )
        )
    ).scalar_one()
    oldest_hours = (
        round((now_utc() - ensure_utc(oldest)).total_seconds() / 3600, 1) if oldest else None
    )

    on_track = sum(1 for e in entries if not e.at_risk)
    at_risk = len(entries) - on_track

    grouped: dict[str, list[RosterEntryOut]] = defaultdict(list)
    for entry in entries:
        grouped[entry.batch_name or "Unassigned"].append(entry)

    batches = [
        BatchStatOut(
            batch_name=name,
            student_count=len(members),
            on_track=sum(1 for m in members if not m.at_risk),
            at_risk=sum(1 for m in members if m.at_risk),
            compliance_pct=round(
                100 * sum(1 for m in members if not m.at_risk) / len(members), 1
            ),
        )
        for name, members in sorted(grouped.items())
    ]

    return CoachStatsOut(
        week_start=week_start,
        week_label=label_for_week(week_start),
        total_students=len(entries),
        pending_reviews=int(pending_total),
        oldest_waiting_hours=oldest_hours,
        on_track=on_track,
        at_risk=at_risk,
        compliance_pct=round(100 * on_track / len(entries), 1) if entries else 0.0,
        batches=batches,
    )
