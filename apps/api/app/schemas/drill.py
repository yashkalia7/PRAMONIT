"""Drill library and weekly assignment payloads."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Difficulty, DrillCategory, MetricType


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DrillOut(_Base):
    id: uuid.UUID
    slug: str
    title: str
    description: str | None = None
    instructions: str | None = None
    category: DrillCategory
    metric_type: MetricType
    target_value: int
    target_label: str = ""
    difficulty: Difficulty
    demo_video_url: str | None = None
    thumbnail_url: str | None = None
    is_global: bool = True


class DrillCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = None
    instructions: str | None = None
    category: DrillCategory = DrillCategory.ball_mastery
    metric_type: MetricType = MetricType.reps
    target_value: int = Field(default=0, ge=0, le=100_000)
    difficulty: Difficulty = Difficulty.beginner
    demo_video_url: str | None = None


class AssignmentItemIn(BaseModel):
    drill_id: uuid.UUID
    required_count: int = Field(default=1, ge=1, le=14)


class AssignmentCreate(BaseModel):
    batch_name: str = Field(min_length=1, max_length=120)
    # Defaults to the current IST week when omitted — the overwhelmingly common
    # case is a coach setting this week's work on a Monday.
    week_start: date | None = None
    notes: str | None = None
    drills: list[AssignmentItemIn] = Field(min_length=1, max_length=10)


class AssignmentItemOut(_Base):
    drill: DrillOut
    required_count: int
    sort_order: int


class AssignmentOut(_Base):
    id: uuid.UUID
    coach_id: uuid.UUID
    batch_name: str
    week_start: date
    week_label: str = ""
    notes: str | None = None
    items: list[AssignmentItemOut] = Field(default_factory=list)


class CurrentAssignmentOut(BaseModel):
    """What the student home screen renders."""

    week_start: date
    week_label: str
    assignment: AssignmentOut | None = None
    # When no coach has set anything this week, the client still shows the
    # global library so a keen student is never blocked from training.
    fallback_drills: list[DrillOut] = Field(default_factory=list)
