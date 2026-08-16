"""The 72-hour auto-approve safety valve, and late-review week attribution."""

from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.timeutil import current_week_start, now_utc, shift_weeks
from app.models.submission import Submission
from app.services.sweeper import run_auto_approve
from tests.conftest import API, auth_headers, register_coach, register_student


def sha(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


async def submit(client, headers, seed: str):
    target = await client.post(
        f"{API}/submissions/upload-url",
        json={"content_type": "video/mp4", "content_hash": sha(seed)},
        headers=headers,
    )
    return await client.post(
        f"{API}/submissions",
        json={
            "video_key": target.json()["video_key"],
            "content_hash": sha(seed),
            "source": "web",
        },
        headers=headers,
    )


async def backdate(session, submission_id, *, hours=None, week_offset=None):
    """Age a submission, and optionally move which week it credits.

    IDs arrive from JSON as strings; the Uuid column binds ``uuid.UUID``.
    """
    submission = (
        await session.execute(
            select(Submission).where(Submission.id == uuid.UUID(str(submission_id)))
        )
    ).scalar_one()
    if hours is not None:
        submission.submitted_at = now_utc() - timedelta(hours=hours)
    if week_offset is not None:
        submission.counts_for_week = shift_weeks(current_week_start(), week_offset)
    await session.commit()
    return submission


async def test_submission_past_the_threshold_is_auto_approved(client, session):
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    sh = auth_headers(student)

    created = (await submit(client, sh, "clip-1")).json()
    await backdate(session, created["id"], hours=settings.AUTO_APPROVE_AFTER_HOURS + 1)

    report = await run_auto_approve(session)
    assert report.approved == 1

    mine = (await client.get(f"{API}/submissions/mine", headers=sh)).json()
    assert mine[0]["status"] == "approved"
    # Tagged, so a coach reviewing later can see this was not their decision.
    assert mine[0]["auto_approved"] is True


async def test_submission_below_the_threshold_is_left_alone(client, session):
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    sh = auth_headers(student)

    created = (await submit(client, sh, "clip-1")).json()
    await backdate(session, created["id"], hours=settings.AUTO_APPROVE_AFTER_HOURS - 1)

    report = await run_auto_approve(session)
    assert report.approved == 0

    mine = (await client.get(f"{API}/submissions/mine", headers=sh)).json()
    assert mine[0]["status"] == "pending"


async def test_auto_approval_rescues_the_weekly_quota_and_the_streak(client, session):
    """A coach going quiet must not cost the student their week."""
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    sh = auth_headers(student)

    for seed in ("clip-1", "clip-2"):
        created = (await submit(client, sh, seed)).json()
        await backdate(session, created["id"], hours=settings.AUTO_APPROVE_AFTER_HOURS + 2)

    before = (await client.get(f"{API}/me/streak", headers=sh)).json()
    assert before["this_week"]["met"] is False

    await run_auto_approve(session)

    after = (await client.get(f"{API}/me/streak", headers=sh)).json()
    assert after["this_week"]["approved_count"] == 2
    assert after["this_week"]["met"] is True
    assert after["current_weeks"] == 1


async def test_a_coach_can_still_reject_after_auto_approval(client, session):
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    sh, ch = auth_headers(student), auth_headers(coach)

    created = (await submit(client, sh, "clip-1")).json()
    await backdate(session, created["id"], hours=settings.AUTO_APPROVE_AFTER_HOURS + 1)
    await run_auto_approve(session)

    review = await client.patch(
        f"{API}/submissions/{created['id']}/review",
        json={"decision": "rejected", "feedback": "Not the assigned drill."},
        headers=ch,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "rejected"
    # The clock badge clears: this is a human decision now.
    assert review.json()["auto_approved"] is False

    streak = (await client.get(f"{API}/me/streak", headers=sh)).json()
    assert streak["this_week"]["approved_count"] == 0
    assert streak["total_points"] == 0


async def test_sweeping_twice_does_not_double_count(client, session):
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    sh = auth_headers(student)

    created = (await submit(client, sh, "clip-1")).json()
    await backdate(session, created["id"], hours=settings.AUTO_APPROVE_AFTER_HOURS + 1)

    assert (await run_auto_approve(session)).approved == 1
    assert (await run_auto_approve(session)).approved == 0

    streak = (await client.get(f"{API}/me/streak", headers=sh)).json()
    assert streak["total_points"] == 10


async def test_late_approval_credits_the_upload_week_not_the_review_week(client, session):
    """A Saturday upload approved the following Tuesday still belongs to Saturday's week.

    Crediting the review week instead would silently move a student's work
    forward and break a streak they had genuinely earned.
    """
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    sh, ch = auth_headers(student), auth_headers(coach)

    last_week = shift_weeks(current_week_start(), -1)

    ids = []
    for seed in ("old-1", "old-2"):
        created = (await submit(client, sh, seed)).json()
        ids.append(created["id"])
        await backdate(session, created["id"], hours=100, week_offset=-1)

    # Reviewed today, days after the week they belong to has closed.
    for submission_id in ids:
        response = await client.patch(
            f"{API}/submissions/{submission_id}/review",
            json={"decision": "approved"},
            headers=ch,
        )
        assert response.status_code == 200
        assert response.json()["counts_for_week"] == last_week.isoformat()

    weeks = (await client.get(f"{API}/me/weeks?limit=3", headers=sh)).json()["weeks"]
    by_start = {w["week_start"]: w for w in weeks}

    assert by_start[last_week.isoformat()]["approved_count"] == 2
    assert by_start[last_week.isoformat()]["met"] is True
    assert by_start[current_week_start().isoformat()]["approved_count"] == 0


async def test_a_week_held_pending_is_provisional_not_broken(client, session):
    """Ended week, quota unmet, videos still queued -> streak is held."""
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    sh, ch = auth_headers(student), auth_headers(coach)

    # Two weeks ago: a clean, met week that establishes a streak.
    for seed in ("w2-a", "w2-b"):
        created = (await submit(client, sh, seed)).json()
        await backdate(session, created["id"], hours=400, week_offset=-2)
        await client.patch(
            f"{API}/submissions/{created['id']}/review",
            json={"decision": "approved"},
            headers=ch,
        )

    # Last week: one approved, one still awaiting review.
    approved = (await submit(client, sh, "w1-a")).json()
    await backdate(session, approved["id"], hours=200, week_offset=-1)
    await client.patch(
        f"{API}/submissions/{approved['id']}/review",
        json={"decision": "approved"},
        headers=ch,
    )
    queued = (await submit(client, sh, "w1-b")).json()
    await backdate(session, queued["id"], hours=200, week_offset=-1)

    # Nudge the recompute through the same path a review would.
    from app.services.progress import refresh_student_progress

    await refresh_student_progress(session, uuid.UUID(approved["student_id"]))
    await session.commit()

    streak = (await client.get(f"{API}/me/streak", headers=sh)).json()
    assert streak["provisional"] is True, "held while the coach still has work queued"

    # The sweeper resolves it, and the streak reconnects across both weeks.
    await run_auto_approve(session)
    resolved = (await client.get(f"{API}/me/streak", headers=sh)).json()
    assert resolved["provisional"] is False
    assert resolved["current_weeks"] >= 2
