"""Streak, week history, leaderboard and coach dashboard payloads."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LeaderboardScope, LeaderboardWindow


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class WeekOut(BaseModel):
    week_start: date
    week_label: str
    approved_count: int = 0
    pending_count: int = 0
    rejected_count: int = 0
    required_count: int = 2
    met: bool = False
    finalised: bool = False
    is_current: bool = False


class StreakOut(BaseModel):
    current_weeks: int = 0
    longest_weeks: int = 0
    last_met_week: date | None = None
    # True when continuation depends on videos still awaiting review, so the UI
    # can say "7 weeks · pending confirmation" instead of guessing.
    provisional: bool = False
    total_approved: int = 0
    total_points: int = 0

    this_week: WeekOut


class WeekHistoryOut(BaseModel):
    weeks: list[WeekOut] = Field(default_factory=list)


class LeaderboardRowOut(BaseModel):
    rank: int
    student_id: uuid.UUID
    full_name: str
    batch_name: str | None = None
    points: int
    current_weeks: int
    approved_total: int
    is_viewer: bool = False


class LeaderboardOut(BaseModel):
    scope: LeaderboardScope
    window: LeaderboardWindow
    week_start: date | None = None
    total_students: int
    rows: list[LeaderboardRowOut] = Field(default_factory=list)
    viewer_row: LeaderboardRowOut | None = None


class RosterEntryOut(BaseModel):
    student_id: uuid.UUID
    full_name: str
    email: str
    batch_name: str | None = None
    course: str | None = None
    jersey_number: int | None = None
    preferred_position: str | None = None
    current_weeks: int = 0
    approved_total: int = 0
    points: int = 0
    this_week_approved: int = 0
    this_week_pending: int = 0
    required_count: int = 2
    at_risk: bool = False
    joined_at: date | None = None


class RosterOut(BaseModel):
    batches: list[str] = Field(default_factory=list)
    students: list[RosterEntryOut] = Field(default_factory=list)


class BatchStatOut(BaseModel):
    batch_name: str
    student_count: int
    on_track: int
    at_risk: int
    compliance_pct: float


class CoachStatsOut(BaseModel):
    week_start: date
    week_label: str
    total_students: int
    pending_reviews: int
    oldest_waiting_hours: float | None = None
    on_track: int
    at_risk: int
    compliance_pct: float
    batches: list[BatchStatOut] = Field(default_factory=list)


class RosterUpdateRequest(BaseModel):
    coach_id: uuid.UUID | None = None
    batch_name: str | None = Field(default=None, max_length=120)
    remove: bool = False
