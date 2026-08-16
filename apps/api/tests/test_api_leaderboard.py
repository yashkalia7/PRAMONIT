"""Leaderboard scopes, windows and the pinned viewer row."""

from __future__ import annotations

import hashlib

import pytest

from tests.conftest import API, auth_headers, register_coach, register_student


def sha(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


async def approved_submissions(client, student_headers, coach_headers, count, prefix):
    for n in range(count):
        seed = f"{prefix}-{n}"
        target = await client.post(
            f"{API}/submissions/upload-url",
            json={"content_type": "video/mp4", "content_hash": sha(seed)},
            headers=student_headers,
        )
        created = (
            await client.post(
                f"{API}/submissions",
                json={
                    "video_key": target.json()["video_key"],
                    "content_hash": sha(seed),
                    "source": "web",
                },
                headers=student_headers,
            )
        ).json()
        await client.patch(
            f"{API}/submissions/{created['id']}/review",
            json={"decision": "approved"},
            headers=coach_headers,
        )


@pytest.fixture
async def academy(client):
    """One coach, two batches, three students with deliberately different effort."""
    coach = await register_coach(client)
    ch = auth_headers(coach)
    coach_id = coach["user"]["id"]

    grinder = await register_student(
        client, coach_id, full_name="Myra Mehta", batch_name="Powai batch"
    )
    steady = await register_student(
        client, coach_id, full_name="Arjun Desai", batch_name="Powai batch"
    )
    slacker = await register_student(
        client, coach_id, full_name="Kabir Rao", batch_name="Andheri batch"
    )

    await approved_submissions(client, auth_headers(grinder), ch, 4, "grind")
    await approved_submissions(client, auth_headers(steady), ch, 2, "steady")
    await approved_submissions(client, auth_headers(slacker), ch, 1, "slack")

    return {
        "coach": coach,
        "ch": ch,
        "grinder": grinder,
        "steady": steady,
        "slacker": slacker,
    }


async def test_academy_board_ranks_by_points(client, academy):
    response = await client.get(
        f"{API}/leaderboard?scope=academy&window=all",
        headers=auth_headers(academy["steady"]),
    )
    assert response.status_code == 200
    rows = response.json()["rows"]

    assert [r["full_name"] for r in rows] == ["Myra Mehta", "Arjun Desai", "Kabir Rao"]
    assert [r["rank"] for r in rows] == [1, 2, 3]
    # 4 approved: 40 + 25 goal + 10 for two extras
    assert rows[0]["points"] == 75
    assert rows[1]["points"] == 45
    assert rows[2]["points"] == 10


async def test_batch_scope_only_shows_the_viewers_batch(client, academy):
    response = await client.get(
        f"{API}/leaderboard?scope=batch&window=all",
        headers=auth_headers(academy["steady"]),
    )
    names = [r["full_name"] for r in response.json()["rows"]]
    assert names == ["Myra Mehta", "Arjun Desai"]
    assert "Kabir Rao" not in names


async def test_coach_scope_covers_every_batch_of_that_coach(client, academy):
    response = await client.get(
        f"{API}/leaderboard?scope=coach&window=all",
        headers=auth_headers(academy["steady"]),
    )
    assert response.json()["total_students"] == 3


async def test_the_viewer_row_is_flagged_and_always_present(client, academy):
    response = await client.get(
        f"{API}/leaderboard?scope=academy&window=all",
        headers=auth_headers(academy["slacker"]),
    )
    body = response.json()
    assert body["viewer_row"]["full_name"] == "Kabir Rao"
    assert body["viewer_row"]["rank"] == 3
    assert any(r["is_viewer"] for r in body["rows"])


async def test_viewer_is_pinned_below_the_cut_when_outside_the_top_n(client, academy):
    """A student in 87th place must still find themselves on the board."""
    response = await client.get(
        f"{API}/leaderboard?scope=academy&window=all&limit=1",
        headers=auth_headers(academy["slacker"]),
    )
    rows = response.json()["rows"]
    assert len(rows) == 2, "top 1, plus the viewer pinned on the end"
    assert rows[0]["rank"] == 1
    assert rows[-1]["is_viewer"] is True
    assert rows[-1]["rank"] == 3


async def test_viewer_is_not_duplicated_when_already_in_the_top_n(client, academy):
    response = await client.get(
        f"{API}/leaderboard?scope=academy&window=all",
        headers=auth_headers(academy["grinder"]),
    )
    rows = response.json()["rows"]
    assert sum(1 for r in rows if r["is_viewer"]) == 1


async def test_students_with_no_points_still_appear(client, academy):
    newcomer = await register_student(
        client, academy["coach"]["user"]["id"], full_name="Ira Nair", batch_name="Powai batch"
    )
    response = await client.get(
        f"{API}/leaderboard?scope=academy&window=all", headers=auth_headers(newcomer)
    )
    rows = response.json()["rows"]
    last = rows[-1]
    assert last["full_name"] == "Ira Nair"
    assert last["points"] == 0
    assert last["is_viewer"] is True


async def test_weekly_window_reports_the_current_week(client, academy):
    response = await client.get(
        f"{API}/leaderboard?scope=academy&window=week",
        headers=auth_headers(academy["steady"]),
    )
    body = response.json()
    assert body["window"] == "week"
    assert body["week_start"] is not None
    # Everything in this fixture was uploaded today, so both windows agree.
    assert body["rows"][0]["points"] == 75


async def test_coach_must_name_a_batch_for_the_batch_scope(client, academy):
    bad = await client.get(f"{API}/leaderboard?scope=batch&window=all", headers=academy["ch"])
    assert bad.status_code == 400

    good = await client.get(
        f"{API}/leaderboard?scope=batch&window=all&batch=Powai%20batch", headers=academy["ch"]
    )
    assert good.status_code == 200
    assert len(good.json()["rows"]) == 2


async def test_leaderboard_requires_authentication(client):
    assert (await client.get(f"{API}/leaderboard")).status_code == 401
