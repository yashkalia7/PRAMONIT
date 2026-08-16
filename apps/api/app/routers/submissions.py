"""Video submission, review queue and coach decisions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import CoachUser, CurrentUser, DbSession, StudentUser
from app.core.timeutil import ensure_utc, label_for_week, now_utc, week_start_for
from app.models.enums import SubmissionStatus, UserRole
from app.models.submission import Submission
from app.models.user import StudentProfile, User
from app.schemas.submission import (
    DrillBrief,
    ReviewQueueOut,
    ReviewRequest,
    SubmissionCreate,
    SubmissionOut,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.progress import refresh_student_progress
from app.services.storage import ALLOWED_MIME_TYPES, build_video_key, get_store

router = APIRouter(prefix="/submissions", tags=["submissions"])

DUPLICATE_DETAIL = (
    "This exact video has already been submitted. Record a new one — "
    "re-uploading previous footage does not count."
)


async def _hash_exists(session, content_hash: str) -> bool:
    return (
        await session.execute(
            select(func.count()).select_from(Submission).where(
                Submission.content_hash == content_hash
            )
        )
    ).scalar_one() > 0


async def _to_out(
    session,
    submission: Submission,
    *,
    with_playback: bool = False,
    student_name: str | None = None,
    batch_name: str | None = None,
) -> SubmissionOut:
    out = SubmissionOut.model_validate(submission)
    out.week_label = label_for_week(submission.counts_for_week)
    out.student_name = student_name
    out.batch_name = batch_name
    if submission.drill is not None:
        out.drill = DrillBrief(
            id=submission.drill.id,
            title=submission.drill.title,
            target_label=submission.drill.target_label,
        )
    if with_playback:
        out.playback_url = await get_store().get_playback_url(submission.video_key)
    return out


@router.post("/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(
    payload: UploadUrlRequest, session: DbSession, student: StudentUser
) -> UploadUrlResponse:
    """Hand back a presigned target — after checking the hash.

    Rejecting a duplicate here rather than on commit means a student who tries to
    resubmit borrowed footage finds out in one round trip, instead of after
    pushing 40 MB over mobile data.
    """
    if payload.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video type {payload.content_type!r}. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    if payload.content_length and payload.content_length > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Video exceeds the {settings.MAX_UPLOAD_MB} MB limit",
        )

    if await _hash_exists(session, payload.content_hash):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DETAIL)

    key = build_video_key(student.id, payload.content_type, now_utc())
    target = await get_store().create_upload_target(
        key=key, content_type=payload.content_type, content_length=payload.content_length
    )
    return UploadUrlResponse(
        upload_url=target.upload_url,
        method=target.method,
        video_key=target.video_key,
        headers=target.headers,
        expires_in=target.expires_in,
        max_bytes=settings.max_upload_bytes,
    )


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    payload: SubmissionCreate, session: DbSession, student: StudentUser
) -> SubmissionOut:
    profile = student.student_profile
    if profile is None or profile.coach_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not attached to a coach yet",
        )

    if await _hash_exists(session, payload.content_hash):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DETAIL)

    submitted_at = now_utc()
    submission = Submission(
        student_id=student.id,
        coach_id=profile.coach_id,
        drill_id=payload.drill_id,
        video_key=payload.video_key,
        content_hash=payload.content_hash,
        duration_sec=payload.duration_sec,
        file_size_bytes=payload.file_size_bytes,
        mime_type=payload.mime_type,
        source=payload.source,
        reps_claimed=payload.reps_claimed,
        student_note=payload.student_note,
        status=SubmissionStatus.pending,
        submitted_at=submitted_at,
        # The week is fixed here, at upload time, and never revisited.
        counts_for_week=week_start_for(submitted_at),
    )
    session.add(submission)

    try:
        await session.flush()
    except IntegrityError as exc:
        # The unique index is the real guard — two uploads racing each other
        # both pass the SELECT above, and only one can pass this.
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DETAIL) from exc

    await refresh_student_progress(session, student.id, {submission.counts_for_week})
    await session.commit()
    await session.refresh(submission)

    return await _to_out(session, submission, with_playback=True)


@router.get("/mine", response_model=list[SubmissionOut])
async def my_submissions(
    session: DbSession,
    student: StudentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SubmissionOut]:
    rows = (
        await session.execute(
            select(Submission)
            .where(Submission.student_id == student.id)
            .order_by(Submission.submitted_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [await _to_out(session, s, with_playback=True) for s in rows]


@router.get("/queue", response_model=ReviewQueueOut)
async def review_queue(
    session: DbSession,
    coach: CoachUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> ReviewQueueOut:
    """Oldest first — the video closest to auto-approving needs a human most."""
    rows = (
        await session.execute(
            select(Submission, User.full_name, StudentProfile.batch_name)
            .join(User, User.id == Submission.student_id)
            .join(StudentProfile, StudentProfile.user_id == Submission.student_id)
            .where(
                Submission.coach_id == coach.id,
                Submission.status == SubmissionStatus.pending,
            )
            .order_by(Submission.submitted_at.asc())
            .limit(limit)
        )
    ).all()

    total = (
        await session.execute(
            select(func.count()).select_from(Submission).where(
                Submission.coach_id == coach.id,
                Submission.status == SubmissionStatus.pending,
            )
        )
    ).scalar_one()

    oldest_hours = None
    if rows:
        oldest = ensure_utc(rows[0][0].submitted_at)
        oldest_hours = round((now_utc() - oldest).total_seconds() / 3600, 1)

    items = [
        await _to_out(session, sub, with_playback=True, student_name=name, batch_name=batch)
        for sub, name, batch in rows
    ]
    return ReviewQueueOut(
        total_pending=int(total), oldest_waiting_hours=oldest_hours, items=items
    )


@router.patch("/{submission_id}/review", response_model=SubmissionOut)
async def review_submission(
    submission_id: uuid.UUID,
    payload: ReviewRequest,
    session: DbSession,
    coach: CoachUser,
) -> SubmissionOut:
    submission = (
        await session.execute(select(Submission).where(Submission.id == submission_id))
    ).scalar_one_or_none()

    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    if submission.coach_id != coach.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This submission belongs to another coach",
        )

    submission.status = payload.decision
    submission.coach_rating = payload.rating
    submission.coach_feedback = payload.feedback
    submission.reviewed_by = coach.id
    submission.reviewed_at = now_utc()
    # A coach overriding an auto-approval should clear the tag: the decision is
    # now a human one and the UI should stop showing the clock badge.
    submission.auto_approved = False

    await session.flush()
    # Recompute the week the video was UPLOADED into, which may be weeks in the
    # past if this review is a late one.
    await refresh_student_progress(session, submission.student_id, {submission.counts_for_week})
    await session.commit()
    await session.refresh(submission)

    return await _to_out(session, submission, with_playback=True)


@router.get("/{submission_id}/playback")
async def playback_url(
    submission_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> dict[str, str | int]:
    submission = (
        await session.execute(select(Submission).where(Submission.id == submission_id))
    ).scalar_one_or_none()
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    owns = submission.student_id == user.id
    coaches = user.role == UserRole.coach and submission.coach_id == user.id
    if not (owns or coaches):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your video")

    url = await get_store().get_playback_url(submission.video_key)
    return {"playback_url": url, "expires_in": 3600}
