"""Domain enumerations.

All of these are persisted as VARCHAR + CHECK constraint rather than native
Postgres ENUM types. Native enums require an ``ALTER TYPE`` dance to add a
value, cannot drop one at all, and do not exist in SQLite — a plain string with
a constraint is portable across both backends and trivially extensible later.
"""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    coach = "coach"
    student = "student"


class RosterStatus(str, enum.Enum):
    active = "active"
    removed = "removed"


class DominantFoot(str, enum.Enum):
    left = "left"
    right = "right"
    both = "both"


class DrillCategory(str, enum.Enum):
    ball_mastery = "ball_mastery"
    passing = "passing"
    shooting = "shooting"
    fitness = "fitness"
    dribbling = "dribbling"


class MetricType(str, enum.Enum):
    reps = "reps"
    duration_sec = "duration_sec"


class Difficulty(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SubmissionSource(str, enum.Enum):
    camera = "camera"
    gallery = "gallery"
    web = "web"


class PointsReason(str, enum.Enum):
    approved_submission = "approved_submission"
    weekly_goal_met = "weekly_goal_met"
    extra_submission = "extra_submission"
    high_rating = "high_rating"
    streak_milestone = "streak_milestone"
    reversal = "reversal"


class LeaderboardScope(str, enum.Enum):
    batch = "batch"
    coach = "coach"
    academy = "academy"


class LeaderboardWindow(str, enum.Enum):
    week = "week"
    all = "all"
