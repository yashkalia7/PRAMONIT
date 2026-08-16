"""Training video submissions — the heart of the app."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutil import now_utc
from app.models.base import Base, enum_type, pk_uuid
from app.models.drill import Drill
from app.models.enums import SubmissionSource, SubmissionStatus


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submission_student_week", "student_id", "counts_for_week"),
        Index("ix_submission_coach_status", "coach_id", "status"),
        Index("ix_submission_status_time", "status", "submitted_at"),
        CheckConstraint(
            "coach_rating IS NULL OR (coach_rating >= 1 AND coach_rating <= 5)",
            name="ck_submission_rating_range",
        ),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Denormalised from the student's profile so the coach's review queue is a
    # single-table index scan, and so history survives a student being moved to
    # a different coach later.
    coach_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    drill_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drills.id", ondelete="SET NULL"))
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("weekly_assignments.id", ondelete="SET NULL")
    )

    video_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512))
    # Globally unique: the same footage can never be submitted twice, by anyone.
    # This is the entire anti-cheat mechanism for v0, so it is enforced by the
    # database rather than by application logic that could be bypassed.
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[SubmissionSource] = mapped_column(
        enum_type(SubmissionSource, "submission_source"),
        default=SubmissionSource.web,
        nullable=False,
    )

    reps_claimed: Mapped[int | None] = mapped_column(Integer)
    student_note: Mapped[str | None] = mapped_column(Text)

    status: Mapped[SubmissionStatus] = mapped_column(
        enum_type(SubmissionStatus, "submission_status"),
        default=SubmissionStatus.pending,
        index=True,
        nullable=False,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coach_rating: Mapped[int | None] = mapped_column(SmallInteger)
    coach_feedback: Mapped[str | None] = mapped_column(Text)

    # Pinned when the video is UPLOADED, never when it is approved. A Saturday
    # upload auto-approved on Tuesday must still credit the week it was filmed
    # in — otherwise a slow coach silently moves a student's work into the
    # wrong week and breaks a streak that was actually earned.
    counts_for_week: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, nullable=False
    )

    drill: Mapped[Drill | None] = relationship(lazy="selectin")

    @property
    def is_counted(self) -> bool:
        return self.status == SubmissionStatus.approved

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Submission {self.id} {self.status.value} week={self.counts_for_week}>"
