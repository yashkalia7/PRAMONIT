"""Coach dashboard: roster, compliance stats, reassignment, and assignments."""

from __future__ import annotations

import hashlib

import pytest

from app.core.timeutil import current_week_start
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


@pytest.fixture
async def squad(client):
    coach = await register_coach(client, batches=["Powai batch", "Andheri batch"])
    ch = auth_headers(coach)
    keen = await register_student(
        client, coach["user"]["id"], full_name="Myra Mehta", batch_name="Powai batch"
    )
    lazy = await register_student(
        client, coach["user"]["id"], full_name="Kabir Rao", batch_name="Andheri batch"
    )
    return {"coach": coach, "ch": ch, "keen": keen, "lazy": lazy}


async def test_roster_lists_students_grouped_by_batch(client, squad):
    response = await client.get(f"{API}/coach/roster", headers=squad["ch"])
    assert response.status_code == 200
    body = response.json()

    assert sorted(body["batches"]) == ["Andheri batch", "Powai batch"]
    assert {s["full_name"] for s in body["students"]} == {"Myra Mehta", "Kabir Rao"}


async def test_a_student_with_nothing_uploaded_is_flagged_at_risk(client, squad):
    body = (await client.get(f"{API}/coach/roster", headers=squad["ch"])).json()
    assert all(s["at_risk"] for s in body["students"])


async def test_pending_uploads_clear_the_at_risk_flag(client, squad):
    """The coach should chase students who haven't filmed, not students waiting on them."""
    await submit(client, auth_headers(squad["keen"]), "clip-1")
    await submit(client, auth_headers(squad["keen"]), "clip-2")

    body = (await client.get(f"{API}/coach/roster", headers=squad["ch"])).json()
    keen = next(s for s in body["students"] if s["full_name"] == "Myra Mehta")
    lazy = next(s for s in body["students"] if s["full_name"] == "Kabir Rao")

    assert keen["this_week_pending"] == 2
    assert keen["at_risk"] is False
    assert lazy["at_risk"] is True


async def test_stats_summarise_compliance_and_the_review_backlog(client, squad):
    await submit(client, auth_headers(squad["keen"]), "clip-1")
    await submit(client, auth_headers(squad["keen"]), "clip-2")

    stats = (await client.get(f"{API}/coach/stats", headers=squad["ch"])).json()
    assert stats["week_start"] == current_week_start().isoformat()
    assert stats["total_students"] == 2
    assert stats["pending_reviews"] == 2
    assert stats["oldest_waiting_hours"] is not None
    assert stats["on_track"] == 1
    assert stats["at_risk"] == 1
    assert stats["compliance_pct"] == 50.0

    by_batch = {b["batch_name"]: b for b in stats["batches"]}
    assert by_batch["Powai batch"]["compliance_pct"] == 100.0
    assert by_batch["Andheri batch"]["compliance_pct"] == 0.0


async def test_a_coach_can_correct_a_students_batch(client, squad):
    response = await client.patch(
        f"{API}/coach/roster/{squad['lazy']['user']['id']}",
        json={"batch_name": "Powai batch"},
        headers=squad["ch"],
    )
    assert response.status_code == 200
    assert response.json()["batch_name"] == "Powai batch"


async def test_reassigning_a_student_moves_their_open_work_too(client, squad):
    """Otherwise the pending video is stranded in the old coach's queue."""
    other = await register_coach(client)
    await submit(client, auth_headers(squad["keen"]), "clip-1")

    assert (
        await client.get(f"{API}/submissions/queue", headers=squad["ch"])
    ).json()["total_pending"] == 1

    response = await client.patch(
        f"{API}/coach/roster/{squad['keen']['user']['id']}",
        json={"coach_id": other["user"]["id"]},
        headers=squad["ch"],
    )
    assert response.status_code == 200

    assert (
        await client.get(f"{API}/submissions/queue", headers=squad["ch"])
    ).json()["total_pending"] == 0
    assert (
        await client.get(f"{API}/submissions/queue", headers=auth_headers(other))
    ).json()["total_pending"] == 1


async def test_removing_a_student_takes_them_off_the_roster(client, squad):
    await client.patch(
        f"{API}/coach/roster/{squad['lazy']['user']['id']}",
        json={"remove": True},
        headers=squad["ch"],
    )
    body = (await client.get(f"{API}/coach/roster", headers=squad["ch"])).json()
    assert {s["full_name"] for s in body["students"]} == {"Myra Mehta"}


async def test_a_coach_cannot_touch_another_coachs_student(client, squad):
    outsider = await register_coach(client)
    response = await client.patch(
        f"{API}/coach/roster/{squad['keen']['user']['id']}",
        json={"remove": True},
        headers=auth_headers(outsider),
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------
# Drills and weekly assignments
# --------------------------------------------------------------------------

async def test_coach_assigns_drills_and_the_student_sees_exactly_those(client, squad):
    made = []
    for title in ("Wall pass — both feet", "Turning with the ball"):
        response = await client.post(
            f"{API}/drills",
            json={"title": title, "metric_type": "reps", "target_value": 200},
            headers=squad["ch"],
        )
        assert response.status_code == 201
        made.append(response.json()["id"])

    assign = await client.post(
        f"{API}/assignments",
        json={
            "batch_name": "Powai batch",
            "notes": "Control before speed.",
            "drills": [{"drill_id": made[0]}, {"drill_id": made[1]}],
        },
        headers=squad["ch"],
    )
    assert assign.status_code == 201
    assert len(assign.json()["items"]) == 2

    current = (
        await client.get(f"{API}/assignments/current", headers=auth_headers(squad["keen"]))
    ).json()
    assert current["assignment"] is not None
    assert current["assignment"]["notes"] == "Control before speed."
    assert [i["drill"]["title"] for i in current["assignment"]["items"]] == [
        "Wall pass — both feet",
        "Turning with the ball",
    ]


async def test_assigning_again_replaces_rather_than_conflicts(client, squad):
    """Coaches revise a week's plan mid-week; that must not be an error."""
    first = (
        await client.post(
            f"{API}/drills", json={"title": "Sole rolls", "target_value": 100}, headers=squad["ch"]
        )
    ).json()["id"]
    second = (
        await client.post(
            f"{API}/drills", json={"title": "Juggles", "target_value": 50}, headers=squad["ch"]
        )
    ).json()["id"]

    for drill_id in (first, second):
        response = await client.post(
            f"{API}/assignments",
            json={"batch_name": "Powai batch", "drills": [{"drill_id": drill_id}]},
            headers=squad["ch"],
        )
        assert response.status_code == 201

    listed = (await client.get(f"{API}/assignments", headers=squad["ch"])).json()
    assert len(listed) == 1, "one assignment per batch per week"
    assert [i["drill"]["title"] for i in listed[0]["items"]] == ["Juggles"]


async def test_unknown_drill_ids_are_rejected(client, squad):
    response = await client.post(
        f"{API}/assignments",
        json={
            "batch_name": "Powai batch",
            "drills": [{"drill_id": "00000000-0000-0000-0000-000000000000"}],
        },
        headers=squad["ch"],
    )
    assert response.status_code == 400


async def test_students_get_the_global_library_when_nothing_is_assigned(client, squad, session):
    """An empty screen reads as 'no training required'. It must never happen."""
    from app.db.seed import DRILLS
    from app.models.drill import Drill
    from app.models.enums import DrillCategory

    for spec in DRILLS[:3]:
        session.add(
            Drill(
                slug=spec["slug"],
                title=spec["title"],
                category=DrillCategory.ball_mastery,
                metric_type=spec["metric_type"],
                target_value=spec["target_value"],
                difficulty=spec["difficulty"],
                is_global=True,
            )
        )
    await session.commit()

    current = (
        await client.get(f"{API}/assignments/current", headers=auth_headers(squad["keen"]))
    ).json()
    assert current["assignment"] is None
    assert len(current["fallback_drills"]) == 3


async def test_students_cannot_create_drills_or_assignments(client, squad):
    sh = auth_headers(squad["keen"])
    assert (
        await client.post(f"{API}/drills", json={"title": "Sneaky drill"}, headers=sh)
    ).status_code == 403
    assert (
        await client.post(
            f"{API}/assignments",
            json={"batch_name": "Powai batch", "drills": [{"drill_id": squad["keen"]["user"]["id"]}]},
            headers=sh,
        )
    ).status_code == 403
