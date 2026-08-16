"""Upload, duplicate blocking, coach review and the approval gate."""

from __future__ import annotations

import hashlib

import pytest

from tests.conftest import API, auth_headers, register_coach, register_student


def sha(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


async def get_upload_url(client, headers, seed: str, **overrides):
    payload = {"content_type": "video/mp4", "content_hash": sha(seed), **overrides}
    return await client.post(f"{API}/submissions/upload-url", json=payload, headers=headers)


async def submit(client, headers, seed: str, **overrides):
    """Full client flow: ask for a target, then commit the record."""
    target = await get_upload_url(client, headers, seed)
    assert target.status_code == 200, target.text
    payload = {
        "video_key": target.json()["video_key"],
        "content_hash": sha(seed),
        "source": "web",
        **overrides,
    }
    return await client.post(f"{API}/submissions", json=payload, headers=headers)


@pytest.fixture
async def pair(client):
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])
    return {
        "coach": coach,
        "student": student,
        "ch": auth_headers(coach),
        "sh": auth_headers(student),
    }


# --------------------------------------------------------------------------
# Upload targets
# --------------------------------------------------------------------------

async def test_upload_url_returns_a_presigned_target(client, pair):
    response = await get_upload_url(client, pair["sh"], "clip-1")
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "PUT"
    assert body["video_key"].startswith("videos/")
    # The client must echo this exact Content-Type or R2 rejects the signature.
    assert body["headers"]["Content-Type"] == "video/mp4"
    assert body["expires_in"] > 0


async def test_unsupported_video_type_is_refused(client, pair):
    response = await get_upload_url(
        client, pair["sh"], "clip-1", content_type="application/pdf"
    )
    assert response.status_code == 415


async def test_malformed_hash_is_rejected(client, pair):
    response = await client.post(
        f"{API}/submissions/upload-url",
        json={"content_type": "video/mp4", "content_hash": "not-a-sha256"},
        headers=pair["sh"],
    )
    assert response.status_code == 422


async def test_oversized_upload_is_refused_before_it_starts(client, pair):
    response = await get_upload_url(
        client, pair["sh"], "clip-1", content_length=10_000_000_000
    )
    assert response.status_code == 413


# --------------------------------------------------------------------------
# Duplicate blocking — the whole anti-cheat story for v0
# --------------------------------------------------------------------------

async def test_duplicate_is_refused_before_any_bytes_are_uploaded(client, pair):
    assert (await submit(client, pair["sh"], "same-clip")).status_code == 201

    retry = await get_upload_url(client, pair["sh"], "same-clip")
    assert retry.status_code == 409
    assert "already been submitted" in retry.json()["detail"]


async def test_duplicate_is_refused_at_commit_time_too(client, pair):
    first = await submit(client, pair["sh"], "same-clip")
    assert first.status_code == 201

    # Skip the pre-check and post straight to the commit endpoint, as a racing
    # second request would.
    response = await client.post(
        f"{API}/submissions",
        json={
            "video_key": "videos/2026/08/whatever.mp4",
            "content_hash": sha("same-clip"),
            "source": "web",
        },
        headers=pair["sh"],
    )
    assert response.status_code == 409


async def test_another_student_cannot_reuse_the_same_footage(client, pair):
    """Sharing one clip around the batch is the obvious cheat. It must fail.

    The block lands at the upload-url step, so the second student is stopped
    before uploading anything at all — the hash index is global, not per-student.
    """
    other = await register_student(client, pair["coach"]["user"]["id"])
    other_headers = auth_headers(other)

    assert (await submit(client, pair["sh"], "shared-clip")).status_code == 201

    blocked = await get_upload_url(client, other_headers, "shared-clip")
    assert blocked.status_code == 409

    # And again at commit, for a client that ignores the pre-check.
    committed = await client.post(
        f"{API}/submissions",
        json={
            "video_key": "videos/2026/08/borrowed.mp4",
            "content_hash": sha("shared-clip"),
            "source": "web",
        },
        headers=other_headers,
    )
    assert committed.status_code == 409


# --------------------------------------------------------------------------
# The approval gate
# --------------------------------------------------------------------------

async def test_new_submission_is_pending_and_pinned_to_the_current_week(client, pair):
    response = await submit(client, pair["sh"], "clip-1", reps_claimed=200)
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "pending"
    assert body["auto_approved"] is False
    assert body["reps_claimed"] == 200

    streak = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert body["counts_for_week"] == streak["this_week"]["week_start"]


async def test_pending_uploads_do_not_count_toward_the_weekly_quota(client, pair):
    await submit(client, pair["sh"], "clip-1")
    await submit(client, pair["sh"], "clip-2")

    streak = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert streak["this_week"]["approved_count"] == 0
    assert streak["this_week"]["pending_count"] == 2
    assert streak["this_week"]["met"] is False
    assert streak["current_weeks"] == 0


async def test_approval_makes_a_submission_count(client, pair):
    created = (await submit(client, pair["sh"], "clip-1")).json()

    review = await client.patch(
        f"{API}/submissions/{created['id']}/review",
        json={"decision": "approved", "rating": 5, "feedback": "Sharp today."},
        headers=pair["ch"],
    )
    assert review.status_code == 200
    assert review.json()["status"] == "approved"

    streak = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert streak["this_week"]["approved_count"] == 1
    assert streak["this_week"]["met"] is False  # quota is 2


async def test_meeting_the_quota_starts_the_streak_and_pays_the_bonus(client, pair):
    for seed in ("clip-1", "clip-2"):
        created = (await submit(client, pair["sh"], seed)).json()
        await client.patch(
            f"{API}/submissions/{created['id']}/review",
            json={"decision": "approved"},
            headers=pair["ch"],
        )

    streak = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert streak["this_week"]["approved_count"] == 2
    assert streak["this_week"]["met"] is True
    assert streak["current_weeks"] == 1
    # 2 approved x10, plus the 25-point weekly goal bonus.
    assert streak["total_points"] == 45


async def test_extra_uploads_beyond_the_quota_pay_less(client, pair):
    for seed in ("clip-1", "clip-2", "clip-3"):
        created = (await submit(client, pair["sh"], seed)).json()
        await client.patch(
            f"{API}/submissions/{created['id']}/review",
            json={"decision": "approved"},
            headers=pair["ch"],
        )

    streak = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    # 3x10 + 25 goal + 5 for the one extra beyond the quota
    assert streak["total_points"] == 60


async def test_high_rating_adds_a_bonus(client, pair):
    created = (await submit(client, pair["sh"], "clip-1")).json()
    await client.patch(
        f"{API}/submissions/{created['id']}/review",
        json={"decision": "approved", "rating": 4},
        headers=pair["ch"],
    )
    streak = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert streak["total_points"] == 15  # 10 approved + 5 rating


async def test_rejection_reverses_points_and_unmeets_the_week(client, pair):
    ids = []
    for seed in ("clip-1", "clip-2"):
        created = (await submit(client, pair["sh"], seed)).json()
        ids.append(created["id"])
        await client.patch(
            f"{API}/submissions/{created['id']}/review",
            json={"decision": "approved"},
            headers=pair["ch"],
        )

    before = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert before["total_points"] == 45

    # The coach watches it again and changes their mind.
    await client.patch(
        f"{API}/submissions/{ids[0]}/review",
        json={"decision": "rejected", "feedback": "Ball out of frame."},
        headers=pair["ch"],
    )

    after = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert after["this_week"]["approved_count"] == 1
    assert after["this_week"]["met"] is False
    assert after["current_weeks"] == 0
    assert after["total_points"] == 10  # goal bonus clawed back


async def test_reviewing_is_idempotent(client, pair):
    """Double-submitting the same decision must not double the points."""
    created = (await submit(client, pair["sh"], "clip-1")).json()
    for _ in range(3):
        await client.patch(
            f"{API}/submissions/{created['id']}/review",
            json={"decision": "approved"},
            headers=pair["ch"],
        )
    streak = (await client.get(f"{API}/me/streak", headers=pair["sh"])).json()
    assert streak["total_points"] == 10


# --------------------------------------------------------------------------
# Review permissions and the queue
# --------------------------------------------------------------------------

async def test_a_coach_cannot_review_another_coachs_student(client, pair):
    outsider = await register_coach(client)
    created = (await submit(client, pair["sh"], "clip-1")).json()

    response = await client.patch(
        f"{API}/submissions/{created['id']}/review",
        json={"decision": "approved"},
        headers=auth_headers(outsider),
    )
    assert response.status_code == 403


async def test_a_student_cannot_review_their_own_work(client, pair):
    created = (await submit(client, pair["sh"], "clip-1")).json()
    response = await client.patch(
        f"{API}/submissions/{created['id']}/review",
        json={"decision": "approved"},
        headers=pair["sh"],
    )
    assert response.status_code == 403


async def test_a_coach_cannot_push_a_submission_back_to_pending(client, pair):
    """That would restart the 72h clock and stall a video indefinitely."""
    created = (await submit(client, pair["sh"], "clip-1")).json()
    response = await client.patch(
        f"{API}/submissions/{created['id']}/review",
        json={"decision": "pending"},
        headers=pair["ch"],
    )
    assert response.status_code == 422


async def test_review_queue_is_oldest_first_and_reports_the_wait(client, pair):
    await submit(client, pair["sh"], "clip-1")
    await submit(client, pair["sh"], "clip-2")

    queue = (await client.get(f"{API}/submissions/queue", headers=pair["ch"])).json()
    assert queue["total_pending"] == 2
    assert queue["oldest_waiting_hours"] is not None
    assert len(queue["items"]) == 2
    assert queue["items"][0]["student_name"] == pair["student"]["user"]["full_name"]
    assert queue["items"][0]["batch_name"] == "Powai batch"
    assert queue["items"][0]["playback_url"]


async def test_queue_only_shows_your_own_students(client, pair):
    outsider = await register_coach(client)
    await submit(client, pair["sh"], "clip-1")

    queue = (
        await client.get(f"{API}/submissions/queue", headers=auth_headers(outsider))
    ).json()
    assert queue["total_pending"] == 0


async def test_approved_work_leaves_the_queue(client, pair):
    created = (await submit(client, pair["sh"], "clip-1")).json()
    await client.patch(
        f"{API}/submissions/{created['id']}/review",
        json={"decision": "approved"},
        headers=pair["ch"],
    )
    queue = (await client.get(f"{API}/submissions/queue", headers=pair["ch"])).json()
    assert queue["total_pending"] == 0


async def test_history_lists_the_students_own_submissions(client, pair):
    await submit(client, pair["sh"], "clip-1", student_note="Wall was wet.")
    mine = (await client.get(f"{API}/submissions/mine", headers=pair["sh"])).json()
    assert len(mine) == 1
    assert mine[0]["student_note"] == "Wall was wet."
    assert mine[0]["week_label"]


async def test_playback_is_denied_to_unrelated_users(client, pair):
    other_coach = await register_coach(client)
    stranger = await register_student(client, other_coach["user"]["id"])
    created = (await submit(client, pair["sh"], "clip-1")).json()

    assert (
        await client.get(
            f"{API}/submissions/{created['id']}/playback", headers=auth_headers(stranger)
        )
    ).status_code == 403
    assert (
        await client.get(f"{API}/submissions/{created['id']}/playback", headers=pair["sh"])
    ).status_code == 200
    assert (
        await client.get(f"{API}/submissions/{created['id']}/playback", headers=pair["ch"])
    ).status_code == 200
