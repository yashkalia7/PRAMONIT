"""Drill library and the coach's weekly batch assignments."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.deps import CoachUser, CurrentUser, DbSession
from app.core.timeutil import current_week_start, label_for_week
from app.models.drill import AssignmentDrill, Drill, WeeklyAssignment
from app.models.enums import Difficulty, DrillCategory, UserRole
from app.schemas.drill import (
    AssignmentCreate,
    AssignmentItemOut,
    AssignmentOut,
    CurrentAssignmentOut,
    DrillCreate,
    DrillOut,
)

router = APIRouter(tags=["drills"])


def _slugify(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{base[:60]}-{uuid.uuid4().hex[:6]}"


def _assignment_out(assignment: WeeklyAssignment) -> AssignmentOut:
    return AssignmentOut(
        id=assignment.id,
        coach_id=assignment.coach_id,
        batch_name=assignment.batch_name,
        week_start=assignment.week_start,
        week_label=label_for_week(assignment.week_start),
        notes=assignment.notes,
        items=[
            AssignmentItemOut(
                drill=DrillOut.model_validate(item.drill),
                required_count=item.required_count,
                sort_order=item.sort_order,
            )
            for item in assignment.items
            if item.drill is not None
        ],
    )


@router.get("/drills", response_model=list[DrillOut])
async def list_drills(
    session: DbSession,
    user: CurrentUser,
    category: DrillCategory | None = None,
    difficulty: Difficulty | None = None,
) -> list[DrillOut]:
    query = select(Drill).order_by(Drill.difficulty, Drill.title)
    if category:
        query = query.where(Drill.category == category)
    if difficulty:
        query = query.where(Drill.difficulty == difficulty)
    # A coach sees the global library plus their own drills; a student sees the
    # global library plus anything their coach authored.
    if user.role == UserRole.coach:
        query = query.where((Drill.is_global.is_(True)) | (Drill.created_by == user.id))
    else:
        coach_id = user.student_profile.coach_id if user.student_profile else None
        query = query.where((Drill.is_global.is_(True)) | (Drill.created_by == coach_id))

    drills = (await session.execute(query)).scalars().all()
    return [DrillOut.model_validate(d) for d in drills]


@router.post("/drills", response_model=DrillOut, status_code=status.HTTP_201_CREATED)
async def create_drill(payload: DrillCreate, session: DbSession, coach: CoachUser) -> DrillOut:
    drill = Drill(
        slug=_slugify(payload.title),
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        category=payload.category,
        metric_type=payload.metric_type,
        target_value=payload.target_value,
        difficulty=payload.difficulty,
        demo_video_url=payload.demo_video_url,
        is_global=False,
        created_by=coach.id,
    )
    session.add(drill)
    await session.commit()
    await session.refresh(drill)
    return DrillOut.model_validate(drill)


@router.get("/assignments/current", response_model=CurrentAssignmentOut)
async def current_assignment(session: DbSession, user: CurrentUser) -> CurrentAssignmentOut:
    """This IST week's work for the caller."""
    week_start = current_week_start()

    if user.role == UserRole.student:
        profile = user.student_profile
        assignment = None
        if profile and profile.coach_id and profile.batch_name:
            assignment = (
                await session.execute(
                    select(WeeklyAssignment)
                    .where(
                        WeeklyAssignment.coach_id == profile.coach_id,
                        WeeklyAssignment.batch_name == profile.batch_name,
                        WeeklyAssignment.week_start == week_start,
                    )
                    .options(
                        selectinload(WeeklyAssignment.items).selectinload(AssignmentDrill.drill)
                    )
                )
            ).scalar_one_or_none()

        fallback: list[DrillOut] = []
        if assignment is None:
            # No assignment set yet this week. Rather than showing an empty
            # screen — which reads as "no training required" — fall back to the
            # global library so a keen student is never blocked.
            drills = (
                await session.execute(
                    select(Drill)
                    .where(Drill.is_global.is_(True))
                    .order_by(Drill.difficulty, Drill.title)
                    .limit(6)
                )
            ).scalars().all()
            fallback = [DrillOut.model_validate(d) for d in drills]

        return CurrentAssignmentOut(
            week_start=week_start,
            week_label=label_for_week(week_start),
            assignment=_assignment_out(assignment) if assignment else None,
            fallback_drills=fallback,
        )

    assignments = (
        await session.execute(
            select(WeeklyAssignment)
            .where(
                WeeklyAssignment.coach_id == user.id,
                WeeklyAssignment.week_start == week_start,
            )
            .options(selectinload(WeeklyAssignment.items).selectinload(AssignmentDrill.drill))
            .order_by(WeeklyAssignment.batch_name)
        )
    ).scalars().all()

    return CurrentAssignmentOut(
        week_start=week_start,
        week_label=label_for_week(week_start),
        assignment=_assignment_out(assignments[0]) if assignments else None,
    )


@router.get("/assignments", response_model=list[AssignmentOut])
async def list_assignments(
    session: DbSession,
    coach: CoachUser,
    batch: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=52),
) -> list[AssignmentOut]:
    query = (
        select(WeeklyAssignment)
        .where(WeeklyAssignment.coach_id == coach.id)
        .options(selectinload(WeeklyAssignment.items).selectinload(AssignmentDrill.drill))
        .order_by(WeeklyAssignment.week_start.desc(), WeeklyAssignment.batch_name)
        .limit(limit)
    )
    if batch:
        query = query.where(WeeklyAssignment.batch_name == batch)
    rows = (await session.execute(query)).scalars().all()
    return [_assignment_out(a) for a in rows]


@router.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def upsert_assignment(
    payload: AssignmentCreate, session: DbSession, coach: CoachUser
) -> AssignmentOut:
    """Set (or replace) one batch's drills for one week.

    Upsert rather than insert: coaches routinely revise a week's plan on Tuesday,
    and a uniqueness error would be a confusing way to tell them so.
    """
    week_start = payload.week_start or current_week_start()

    drill_ids = [item.drill_id for item in payload.drills]
    found = (
        await session.execute(select(Drill.id).where(Drill.id.in_(drill_ids)))
    ).scalars().all()
    missing = set(drill_ids) - set(found)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown drill id(s): {', '.join(str(m) for m in missing)}",
        )

    assignment = (
        await session.execute(
            select(WeeklyAssignment).where(
                WeeklyAssignment.coach_id == coach.id,
                WeeklyAssignment.batch_name == payload.batch_name,
                WeeklyAssignment.week_start == week_start,
            )
        )
    ).scalar_one_or_none()

    if assignment is None:
        assignment = WeeklyAssignment(
            coach_id=coach.id, batch_name=payload.batch_name, week_start=week_start
        )
        session.add(assignment)
        await session.flush()

    assignment.notes = payload.notes

    # Rebuild the drill list with explicit statements rather than by mutating
    # ``assignment.items``. Touching that relationship on an already-flushed
    # object triggers a lazy load, and a lazy load from synchronous attribute
    # access inside async code raises MissingGreenlet.
    await session.execute(
        delete(AssignmentDrill).where(AssignmentDrill.assignment_id == assignment.id)
    )
    for order, item in enumerate(payload.drills):
        session.add(
            AssignmentDrill(
                assignment_id=assignment.id,
                drill_id=item.drill_id,
                required_count=item.required_count,
                sort_order=order,
            )
        )

    await session.commit()

    fresh = (
        await session.execute(
            select(WeeklyAssignment)
            .where(WeeklyAssignment.id == assignment.id)
            .options(selectinload(WeeklyAssignment.items).selectinload(AssignmentDrill.drill))
        )
    ).scalar_one()
    return _assignment_out(fresh)
