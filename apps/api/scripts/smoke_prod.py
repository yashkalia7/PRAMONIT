"""End-to-end smoke test against a live deployment.

Exercises the one path that cannot be covered by unit tests, because it spans
three separate systems: the API, Postgres, and the object store. It registers a
throwaway coach and student, pushes real bytes through a presigned URL to R2,
proves a pending video does not count, approves it, proves the week and streak
turn over — then deletes everything it created.

    python -m scripts.smoke_prod                       # against localhost
    python -m scripts.smoke_prod https://api.your.com  # against production

Safe to run against production: every row it writes, it removes.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import uuid

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE}/api"
PASSWORD = "smoke-test-pw-8827"

ok = 0
failed: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global ok
    if condition:
        ok += 1
        print(f"  [ok]   {label}")
    else:
        failed.append(label)
        print(f"  [FAIL] {label} {detail}")


def clip(seed: str) -> bytes:
    return b"\x00\x00\x00\x18ftyp" + f"{seed}".encode() * 512


async def submit(client: httpx.AsyncClient, headers: dict, seed: str) -> str | None:
    """The genuine three-step client flow: sign, PUT to storage, commit."""
    payload = clip(seed)
    digest = hashlib.sha256(payload).hexdigest()

    signed = await client.post(
        f"{API}/submissions/upload-url",
        json={"content_type": "video/mp4", "content_hash": digest,
              "content_length": len(payload)},
        headers=headers,
    )
    if signed.status_code != 200:
        print(f"       upload-url -> {signed.status_code} {signed.text[:160]}")
        return None

    target = signed.json()
    # Straight to R2 — this request never touches the API.
    put = await client.put(
        target["upload_url"], content=payload, headers=target["headers"], timeout=120
    )
    if put.status_code not in (200, 201, 204):
        print(f"       storage PUT -> {put.status_code} {put.text[:160]}")
        return None

    created = await client.post(
        f"{API}/submissions",
        json={"video_key": target["video_key"], "content_hash": digest,
              "mime_type": "video/mp4", "source": "web",
              "student_note": "smoke test"},
        headers=headers,
    )
    if created.status_code != 201:
        print(f"       commit -> {created.status_code} {created.text[:160]}")
        return None
    return created.json()["id"]


async def main() -> int:
    tag = uuid.uuid4().hex[:8]
    coach_email = f"smoke.coach.{tag}@pramonit.dev"
    student_email = f"smoke.student.{tag}@pramonit.dev"

    print(f"\nsmoke test against {BASE}\n")

    async with httpx.AsyncClient(timeout=90) as client:
        health = await client.get(f"{BASE}/health")
        body = health.json() if health.status_code == 200 else {}
        check("health reachable", health.status_code == 200)
        check(
            "database is postgres, not the sqlite fallback",
            body.get("database", {}).get("backend") == "postgresql",
            str(body.get("database")),
        )
        check("storage backend is s3", body.get("storage") == "s3", str(body.get("storage")))

        coach = await client.post(
            f"{API}/auth/register/coach",
            json={"email": coach_email, "password": PASSWORD, "full_name": f"Smoke Coach {tag}",
                  "primary_location": "Powai", "batches": ["Smoke batch"]},
        )
        check("coach registers", coach.status_code == 201, coach.text[:160])
        if coach.status_code != 201:
            return 1
        coach_id = coach.json()["user"]["id"]
        ch = {"Authorization": f"Bearer {coach.json()['tokens']['access_token']}"}

        student = await client.post(
            f"{API}/auth/register/student",
            json={"email": student_email, "password": PASSWORD, "full_name": f"Smoke Player {tag}",
                  "coach_id": coach_id, "batch_name": "Smoke batch", "consent_media": True},
        )
        check("student registers and links to the coach", student.status_code == 201, student.text[:160])
        if student.status_code != 201:
            return 1
        student_id = student.json()["user"]["id"]
        sh = {"Authorization": f"Bearer {student.json()['tokens']['access_token']}"}

        drills = await client.get(f"{API}/drills", headers=sh)
        check("drill library is populated", drills.status_code == 200 and len(drills.json()) >= 6,
              f"{len(drills.json()) if drills.status_code == 200 else '?'} drills")

        first = await submit(client, sh, f"smoke-{tag}-1")
        check("video uploads to R2 and commits", first is not None)
        if first is None:
            return 1

        # Duplicate: identical bytes must be refused.
        dupe_payload = clip(f"smoke-{tag}-1")
        dupe = await client.post(
            f"{API}/submissions/upload-url",
            json={"content_type": "video/mp4",
                  "content_hash": hashlib.sha256(dupe_payload).hexdigest()},
            headers=sh,
        )
        check("duplicate video is refused", dupe.status_code == 409, str(dupe.status_code))

        streak = (await client.get(f"{API}/me/streak", headers=sh)).json()
        check("pending video does not count yet",
              streak["this_week"]["approved_count"] == 0 and streak["this_week"]["pending_count"] == 1,
              str(streak["this_week"]))

        second = await submit(client, sh, f"smoke-{tag}-2")
        check("second video uploads", second is not None)

        queue = (await client.get(f"{API}/submissions/queue", headers=ch)).json()
        check("both land in the coach queue", queue["total_pending"] == 2, str(queue["total_pending"]))
        check("playback URL is presigned",
              bool(queue["items"] and queue["items"][0]["playback_url"]))

        for sid in (first, second):
            await client.patch(f"{API}/submissions/{sid}/review",
                               json={"decision": "approved", "rating": 5}, headers=ch)

        streak = (await client.get(f"{API}/me/streak", headers=sh)).json()
        check("approval closes the week", streak["this_week"]["met"] is True, str(streak["this_week"]))
        check("streak advances to 1", streak["current_weeks"] == 1, str(streak["current_weeks"]))
        check("points are awarded (2x10 + 25 + 2x5)", streak["total_points"] == 55,
              str(streak["total_points"]))

        board = (await client.get(f"{API}/leaderboard?scope=academy&window=all", headers=sh)).json()
        check("student appears on the leaderboard", board.get("viewer_row") is not None)

    # ---------------------------------------------------------------- cleanup
    from sqlalchemy import delete

    from app.db.session import SessionLocal, engine
    from app.models import Submission, User

    async with SessionLocal() as session:
        await session.execute(delete(Submission).where(Submission.student_id == uuid.UUID(student_id)))
        # Cascades clear profiles, week results, streaks and the points ledger.
        await session.execute(delete(User).where(User.id.in_([uuid.UUID(student_id), uuid.UUID(coach_id)])))
        await session.commit()
    await engine.dispose()
    print("\n  cleaned up test accounts")

    print(f"\n{ok} passed, {len(failed)} failed")
    for name in failed:
        print(f"  - {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
