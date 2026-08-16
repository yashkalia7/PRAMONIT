"""Derived progress state: points ledger, per-week results, cached streaks."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now_utc
from app.models.base import Base, enum_type, pk_uuid
from app.models.enums import PointsReason


class PointsLedger(Base):
    """Append-only points journal.

    Never updated or deleted. A rejection after approval writes a compensating
    negative row, so every number on the leaderboard can be traced to the events
    that produced it — which matters the first time a parent disputes a ranking.
    """

    __tablename__ = "points_ledger"
    __table_args__ = (
        Index("ix_points_student_week", "student_id", "week_start"),
        Index("ix_points_week", "week_start"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE")
    )
    reason: Mapped[PointsReason] = mapped_column(
        enum_type(PointsReason, "points_reason"), nullable=False
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    detail: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, nullable=False
    )


class WeekResult(Base):
    """One row per student per week: did they meet the club's minimum?

    ``finalised`` is the subtle field. A week is only finalised once it has
    ended AND no submission of its is still pending review. Until then the week
    can neither extend nor break a streak, which is what stops a slow coach from
    destroying a student's record.
    """

    __tablename__ = "week_results"
    __table_args__ = (
        UniqueConstraint("student_id", "week_start", name="uq_week_result"),
        Index("ix_week_result_week", "week_start"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)

    approved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    required_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    met: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finalised: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False
    )


class StudentStreak(Base):
    """Cached streak so the home screen is one row read, not a scan."""

    __tablename__ = "student_streaks"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    current_weeks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_weeks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_met_week: Mapped[date | None] = mapped_column(Date)
    # True when the streak's continuation depends on videos still awaiting
    # review. The UI shows "7 weeks · pending confirmation" rather than lying in
    # either direction.
    provisional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_approved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False
    )
