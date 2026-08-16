"""Upload, submission and review payloads."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SubmissionSource, SubmissionStatus

HEX64 = re.compile(r"^[0-9a-f]{64}$")


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UploadUrlRequest(BaseModel):
    content_type: str = Field(default="video/mp4", max_length=120)
    content_length: int | None = Field(default=None, ge=1)
    # SHA-256 of the file, computed on the client. Sent *before* the upload so a
    # duplicate is refused in one round trip instead of after 40 MB has crossed
    # a mobile connection.
    content_hash: str = Field(min_length=64, max_length=64)

    @field_validator("content_hash")
    @classmethod
    def _hex(cls, v: str) -> str:
        v = v.strip().lower()
        if not HEX64.match(v):
            raise ValueError("content_hash must be a 64-character hex SHA-256 digest")
        return v


class UploadUrlResponse(BaseModel):
    upload_url: str
    method: str
    video_key: str
    headers: dict[str, str] = Field(default_factory=dict)
    expires_in: int
    max_bytes: int


class SubmissionCreate(BaseModel):
    video_key: str = Field(min_length=3, max_length=512)
    content_hash: str = Field(min_length=64, max_length=64)
    drill_id: uuid.UUID | None = None
    duration_sec: int | None = Field(default=None, ge=0, le=7200)
    file_size_bytes: int | None = Field(default=None, ge=0)
    mime_type: str | None = Field(default=None, max_length=120)
    source: SubmissionSource = SubmissionSource.web
    reps_claimed: int | None = Field(default=None, ge=0, le=100_000)
    student_note: str | None = Field(default=None, max_length=2000)

    @field_validator("content_hash")
    @classmethod
    def _hex(cls, v: str) -> str:
        v = v.strip().lower()
        if not HEX64.match(v):
            raise ValueError("content_hash must be a 64-character hex SHA-256 digest")
        return v


class DrillBrief(_Base):
    id: uuid.UUID
    title: str
    target_label: str = ""


class SubmissionOut(_Base):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str | None = None
    batch_name: str | None = None
    coach_id: uuid.UUID | None = None
    drill: DrillBrief | None = None
    status: SubmissionStatus
    source: SubmissionSource
    duration_sec: int | None = None
    reps_claimed: int | None = None
    student_note: str | None = None
    coach_rating: int | None = None
    coach_feedback: str | None = None
    auto_approved: bool = False
    reviewed_at: datetime | None = None
    counts_for_week: date
    week_label: str = ""
    submitted_at: datetime
    playback_url: str | None = None


class ReviewRequest(BaseModel):
    # 'approved' or 'rejected' only — a coach cannot push something back to
    # pending, which would restart the 72-hour auto-approve clock and could be
    # used to stall a submission indefinitely.
    decision: SubmissionStatus
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback: str | None = Field(default=None, max_length=2000)

    @field_validator("decision")
    @classmethod
    def _terminal(cls, v: SubmissionStatus) -> SubmissionStatus:
        if v == SubmissionStatus.pending:
            raise ValueError("decision must be 'approved' or 'rejected'")
        return v


class ReviewQueueOut(BaseModel):
    total_pending: int
    oldest_waiting_hours: float | None = None
    items: list[SubmissionOut] = Field(default_factory=list)
