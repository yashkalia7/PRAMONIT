"""Seed the academy.

Creates the ball-mastery drill library, the hardcoded coach list that populates
the signup dropdown, and a demo cohort carrying ten weeks of training history —
so the streak strip, the compliance dashboard and all six leaderboard tabs have
something real to render the first time the app is opened.

    python -m app.db.seed          # create if empty
    python -m app.db.seed --reset  # wipe and rebuild

Every demo account shares one password, printed at the end.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from app.core.security import hash_password
from app.core.timeutil import IST, UTC, current_week_start, shift_weeks
from app.models.drill import AssignmentDrill, Drill, WeeklyAssignment
from app.models.enums import (
    Difficulty,
    DominantFoot,
    DrillCategory,
    MetricType,
    RosterStatus,
    SubmissionSource,
    SubmissionStatus,
    UserRole,
)
from app.models.submission import Submission
from app.models.user import CoachProfile, StudentProfile, User

DEMO_PASSWORD = "pramonit123"
HISTORY_WEEKS = 10
MIN_PENDING_PER_COACH = 3

# ---------------------------------------------------------------------------
# Hardcoded for now, as agreed. Replace with the club's real coaches and batch
# names — this list is the only place they appear.
# ---------------------------------------------------------------------------
COACHES = [
    {
        "email": "rahul@pramonit.dev",
        "full_name": "Rahul Menon",
        "specialization": "Ball mastery & first touch",
        "primary_location": "Powai",
        "years_experience": 9,
        "qualifications": "AFC 'C' Licence, AIFF Grassroots",
        "bio": "Former state-level midfielder. Obsessive about the weaker foot.",
        "batches": ["Powai batch", "Powai evening batch"],
    },
    {
        "email": "sameer@pramonit.dev",
        "full_name": "Sameer Qureshi",
        "specialization": "Dribbling & 1v1",
        "primary_location": "Andheri",
        "years_experience": 6,
        "qualifications": "AIFF 'D' Licence",
        "bio": "Believes every session should end with a game.",
        "batches": ["Andheri batch"],
    },
    {
        "email": "neha@pramonit.dev",
        "full_name": "Neha Kulkarni",
        "specialization": "Technique & conditioning",
        "primary_location": "Bandra",
        "years_experience": 11,
        "qualifications": "AFC 'B' Licence, Sports Science MSc",
        "bio": "Ex-national camp coach. Big on measurable weekly targets.",
        "batches": ["Bandra batch"],
    },
]

DRILLS = [
    {
        "slug": "wall-pass-both-feet-200",
        "title": "Wall pass — both feet",
        "description": "200 controlled passes against a wall, alternating feet.",
        "instructions": (
            "Stand 2–3 m from a flat wall. Pass with the inside of the foot, "
            "control with the other. Alternate every touch. Keep the ball below "
            "knee height. Film from the side so both feet are visible."
        ),
        "metric_type": MetricType.reps,
        "target_value": 200,
        "difficulty": Difficulty.beginner,
    },
    {
        "slug": "one-tap-juggles-wall-50",
        "title": "One-tap juggles on the wall",
        "description": "50 continuous one-touch returns off the wall.",
        "instructions": (
            "No ground bounce between touches. Use laces or inside foot. "
            "Restart the count on a drop — film the whole attempt unbroken."
        ),
        "metric_type": MetricType.reps,
        "target_value": 50,
        "difficulty": Difficulty.intermediate,
    },
    {
        "slug": "turning-with-the-ball-3min",
        "title": "Turning with the ball",
        "description": "3 minutes of continuous turns — Cruyff, drag-back, inside hook.",
        "instructions": (
            "Set two cones 8 m apart. Drive, turn, drive back. Rotate the turn "
            "type every length. Head up between touches."
        ),
        "metric_type": MetricType.duration_sec,
        "target_value": 180,
        "difficulty": Difficulty.beginner,
    },
    {
        "slug": "sole-rolls-100",
        "title": "Sole rolls",
        "description": "100 sole-of-the-foot rolls, alternating feet.",
        "instructions": "Ball under control, small touches, stay on the balls of your feet.",
        "metric_type": MetricType.reps,
        "target_value": 100,
        "difficulty": Difficulty.beginner,
    },
    {
        "slug": "inside-outside-touches-100",
        "title": "Inside–outside touches",
        "description": "100 touches alternating inside and outside of the same foot.",
        "instructions": "Complete 50 on the right, then 50 on the left. Keep the ball tight.",
        "metric_type": MetricType.reps,
        "target_value": 100,
        "difficulty": Difficulty.intermediate,
    },
    {
        "slug": "figure-eight-dribble-2min",
        "title": "Figure-eight dribble",
        "description": "2 minutes weaving a figure of eight through two cones.",
        "instructions": "Cones 2 m apart. Small touches, both feet, no stopping.",
        "metric_type": MetricType.duration_sec,
        "target_value": 120,
        "difficulty": Difficulty.advanced,
    },
]

FIRST_NAMES = [
    "Arjun", "Ishaan", "Kabir", "Vivaan", "Aditya", "Rohan", "Ayaan", "Dev",
    "Zara", "Anaya", "Myra", "Aarav", "Reyansh", "Kiaan", "Saanvi", "Ira",
]
LAST_NAMES = ["Mehta", "Kapoor", "Iyer", "Nair", "Sharma", "Desai", "Rao", "Joshi"]
POSITIONS = ["Striker", "Winger", "Attacking midfielder", "Centre back", "Full back", "Keeper"]
SCHOOLS = ["Hiranandani Foundation School", "Bombay Scottish", "Podar International", "Ryan International"]

# Training consistency per student, as a probability of hitting the weekly
# quota. Spread deliberately wide so the leaderboard and the "at risk" panel
# both have something to show.
CONSISTENCY_TIERS = [0.98, 0.95, 0.9, 0.85, 0.75, 0.7, 0.6, 0.5, 0.45, 0.35, 0.3, 0.2]


def _demo_hash(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


async def _already_seeded(session) -> bool:
    count = (
        await session.execute(select(func.count()).select_from(User))
    ).scalar_one()
    return count > 0


async def seed(session, *, rng: random.Random | None = None) -> dict[str, object]:
    rng = rng or random.Random(20260810)
    this_week = current_week_start()

    # ---------------------------------------------------------------- drills
    drills: list[Drill] = []
    for spec in DRILLS:
        drill = Drill(
            slug=spec["slug"],
            title=spec["title"],
            description=spec["description"],
            instructions=spec["instructions"],
            category=DrillCategory.ball_mastery,
            metric_type=spec["metric_type"],
            target_value=spec["target_value"],
            difficulty=spec["difficulty"],
            is_global=True,
        )
        session.add(drill)
        drills.append(drill)

    # --------------------------------------------------------------- coaches
    coaches: list[User] = []
    for spec in COACHES:
        coach = User(
            email=spec["email"],
            password_hash=hash_password(DEMO_PASSWORD),
            role=UserRole.coach,
            full_name=spec["full_name"],
            phone="+91 98200 00000",
        )
        coach.coach_profile = CoachProfile(
            bio=spec["bio"],
            qualifications=spec["qualifications"],
            years_experience=spec["years_experience"],
            specialization=spec["specialization"],
            primary_location=spec["primary_location"],
            batches=spec["batches"],
        )
        session.add(coach)
        coaches.append(coach)

    await session.flush()

    # -------------------------------------------------------------- students
    students: list[tuple[User, float]] = []
    used_names: set[str] = set()

    for index, consistency in enumerate(CONSISTENCY_TIERS):
        coach = coaches[index % len(coaches)]
        batch = coach.coach_profile.batches[index % len(coach.coach_profile.batches)]

        while True:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break

        slug = name.lower().replace(" ", ".")
        student = User(
            email=f"{slug}@pramonit.dev",
            password_hash=hash_password(DEMO_PASSWORD),
            role=UserRole.student,
            full_name=name,
            phone=f"+91 9{rng.randint(100000000, 999999999)}",
            dob=date(rng.randint(2008, 2014), rng.randint(1, 12), rng.randint(1, 28)),
        )
        student.student_profile = StudentProfile(
            coach_id=coach.id,
            roster_status=RosterStatus.active,
            batch_name=batch,
            course="Ball Mastery — Foundation",
            jersey_number=rng.randint(1, 99),
            preferred_position=rng.choice(POSITIONS),
            dominant_foot=rng.choice(list(DominantFoot)),
            height_cm=rng.randint(130, 180),
            weight_kg=round(rng.uniform(28, 70), 1),
            years_playing=rng.randint(1, 8),
            school_name=rng.choice(SCHOOLS),
            guardian_name=f"{rng.choice(['Mr.', 'Mrs.'])} {name.split()[1]}",
            guardian_phone=f"+91 9{rng.randint(100000000, 999999999)}",
            emergency_contact=f"+91 9{rng.randint(100000000, 999999999)}",
            consent_media=True,
            joined_at=this_week - timedelta(weeks=HISTORY_WEEKS + 2),
        )
        session.add(student)
        students.append((student, consistency))

    await session.flush()

    # ----------------------------------------------------------- assignments
    for coach in coaches:
        for batch in coach.coach_profile.batches:
            for offset in range(-3, 1):
                week = shift_weeks(this_week, offset)
                assignment = WeeklyAssignment(
                    coach_id=coach.id,
                    batch_name=batch,
                    week_start=week,
                    notes="Focus on control before speed. Film from the side.",
                )
                session.add(assignment)
                await session.flush()
                for order, drill in enumerate(rng.sample(drills, k=3)):
                    session.add(
                        AssignmentDrill(
                            assignment_id=assignment.id,
                            drill_id=drill.id,
                            required_count=1,
                            sort_order=order,
                        )
                    )

    # ------------------------------------------------------------ submissions
    submission_count = 0
    pending_by_coach: Counter = Counter()
    roster_by_coach: dict = defaultdict(list)
    for student, _ in students:
        roster_by_coach[student.student_profile.coach_id].append(student)

    for student, consistency in students:
        for offset in range(-HISTORY_WEEKS, 1):
            week = shift_weeks(this_week, offset)
            is_current = offset == 0

            if rng.random() < consistency:
                uploads = rng.choices([2, 3, 4, 5], weights=[45, 30, 15, 10])[0]
            else:
                uploads = rng.choice([0, 1, 1])

            if is_current:
                # Partial progress through the week in progress, so the home
                # screen shows a genuine "1 of 2" rather than a finished week.
                uploads = min(uploads, rng.choice([0, 1, 1, 2, 3]))

            for n in range(uploads):
                day = rng.randint(0, 6 if not is_current else max(0, datetime.now(IST).weekday()))
                submitted_local = datetime.combine(
                    week + timedelta(days=day),
                    datetime.min.time(),
                    tzinfo=IST,
                ) + timedelta(hours=rng.randint(6, 21), minutes=rng.randint(0, 59))
                submitted_at = submitted_local.astimezone(UTC)

                if is_current:
                    # Some of this week's work is still queued, which is what
                    # gives the coach a non-empty review queue on first login.
                    status_choice = rng.choices(
                        [SubmissionStatus.approved, SubmissionStatus.pending],
                        weights=[55, 45],
                    )[0]
                else:
                    status_choice = rng.choices(
                        [SubmissionStatus.approved, SubmissionStatus.rejected],
                        weights=[92, 8],
                    )[0]

                drill = rng.choice(drills)
                rating = rng.choice([3, 4, 4, 5]) if status_choice == SubmissionStatus.approved else None

                session.add(
                    Submission(
                        student_id=student.id,
                        coach_id=student.student_profile.coach_id,
                        drill_id=drill.id,
                        video_key="videos/demo/placeholder.mp4",
                        content_hash=_demo_hash(student.email, week, n),
                        duration_sec=rng.randint(25, 110),
                        file_size_bytes=rng.randint(4_000_000, 30_000_000),
                        mime_type="video/mp4",
                        source=rng.choice(list(SubmissionSource)),
                        reps_claimed=drill.target_value,
                        student_note=rng.choice(
                            [None, "Left foot felt better today.", "Wall was wet, still finished.",
                             "Struggled with the last 30.", "New personal best."]
                        ),
                        status=status_choice,
                        coach_rating=rating,
                        coach_feedback=(
                            rng.choice([None, "Good tempo. Head up more.", "Weaker foot improving."])
                            if status_choice == SubmissionStatus.approved
                            else "Ball out of frame — refilm from the side."
                        ),
                        reviewed_at=submitted_local + timedelta(hours=rng.randint(2, 40))
                        if status_choice != SubmissionStatus.pending
                        else None,
                        reviewed_by=student.student_profile.coach_id
                        if status_choice != SubmissionStatus.pending
                        else None,
                        counts_for_week=week,
                        submitted_at=submitted_at,
                    )
                )
                submission_count += 1
                if is_current and status_choice == SubmissionStatus.pending:
                    pending_by_coach[student.student_profile.coach_id] += 1

    # Guarantee every coach opens the app with something to review. A demo that
    # lands on "queue clear" hides the single feature the club cares most about,
    # and whether the random walk above left a queue is pure chance.
    for coach in coaches:
        roster = roster_by_coach.get(coach.id, [])
        if not roster:
            continue
        for n in range(max(0, MIN_PENDING_PER_COACH - pending_by_coach[coach.id])):
            student = roster[n % len(roster)]
            drill = rng.choice(drills)
            submitted_local = datetime.combine(
                this_week + timedelta(days=min(datetime.now(IST).weekday(), 6)),
                datetime.min.time(),
                tzinfo=IST,
            ) + timedelta(hours=rng.randint(7, 20), minutes=rng.randint(0, 59))
            session.add(
                Submission(
                    student_id=student.id,
                    coach_id=coach.id,
                    drill_id=drill.id,
                    video_key="videos/demo/placeholder.mp4",
                    content_hash=_demo_hash("queue", coach.email, n),
                    duration_sec=rng.randint(30, 95),
                    file_size_bytes=rng.randint(5_000_000, 25_000_000),
                    mime_type="video/mp4",
                    source=rng.choice(list(SubmissionSource)),
                    reps_claimed=drill.target_value,
                    student_note=rng.choice(
                        [None, "Think I hit the target this time.", "Wall was busy, did it at home."]
                    ),
                    status=SubmissionStatus.pending,
                    counts_for_week=this_week,
                    submitted_at=submitted_local.astimezone(UTC),
                )
            )
            submission_count += 1

    await session.flush()

    # ------------------------------------------------- derive all progress
    from app.services.progress import refresh_student_progress

    for student, _ in students:
        await refresh_student_progress(session, student.id)

    await session.commit()

    return {
        "coaches": len(coaches),
        "students": len(students),
        "drills": len(drills),
        "submissions": submission_count,
    }


async def main(reset: bool = False) -> None:
    from app.db.init_db import create_all, drop_all
    from app.db.session import SessionLocal, backend_name

    print(f"database backend: {backend_name()}")

    if reset:
        await drop_all()
        print("dropped existing schema")
    await create_all()

    async with SessionLocal() as session:
        if not reset and await _already_seeded(session):
            print("database already contains users — nothing to do (use --reset to rebuild)")
            return
        stats = await seed(session)

    print(
        f"\nseeded {stats['coaches']} coaches, {stats['students']} students, "
        f"{stats['drills']} drills, {stats['submissions']} submissions"
    )
    print("\n  demo logins (password for every account below):")
    print(f"    password : {DEMO_PASSWORD}")
    for spec in COACHES:
        print(f"    coach    : {spec['email']:<28} {spec['full_name']}")
    print("    students : <firstname>.<lastname>@pramonit.dev")
    print("               run  GET /api/public/coaches  or open the app to see the roster\n")


if __name__ == "__main__":  # pragma: no cover - operator entry point
    parser = argparse.ArgumentParser(description="Seed the Pramonit academy database")
    parser.add_argument("--reset", action="store_true", help="drop and rebuild the schema first")
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))
