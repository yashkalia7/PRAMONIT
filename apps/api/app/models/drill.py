"""The ball-mastery drill library and the coach's weekly batch assignments."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_type, pk_uuid
from app.models.enums import Difficulty, DrillCategory, MetricType


class Drill(Base, TimestampMixin):
    """A single trainable exercise, e.g. 'Wall pass, both feet — 200 reps'.

    Seeded globally (``is_global``) so every coach starts with a usable library;
    coaches may also author their own.
    """

    __tablename__ = "drills"

    id: Mapped[uuid.UUID] = pk_uuid()
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)

    category: Mapped[DrillCategory] = mapped_column(
        enum_type(DrillCategory, "drill_category"),
        default=DrillCategory.ball_mastery,
        nullable=False,
    )
    metric_type: Mapped[MetricType] = mapped_column(
        enum_type(MetricType, "metric_type"), default=MetricType.reps, nullable=False
    )
    target_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        enum_type(Difficulty, "difficulty"), default=Difficulty.beginner, nullable=False
    )

    demo_video_url: Mapped[str | None] = mapped_column(String(512))
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    is_global: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    @property
    def target_label(self) -> str:
        if self.metric_type == MetricType.duration_sec:
            minutes, seconds = divmod(self.target_value, 60)
            return f"{minutes} min" if not seconds else f"{minutes}m {seconds}s"
        return f"{self.target_value} reps"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Drill {self.slug}>"


class WeeklyAssignment(Base, TimestampMixin):
    """What a coach set for one batch in one IST week."""

    __tablename__ = "weekly_assignments"
    __table_args__ = (
        UniqueConstraint("coach_id", "batch_name", "week_start", name="uq_assignment_batch_week"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    coach_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    batch_name: Mapped[str] = mapped_column(String(120), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["AssignmentDrill"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignmentDrill.sort_order",
        lazy="selectin",
    )


class AssignmentDrill(Base):
    """Join row: one drill inside one weekly assignment."""

    __tablename__ = "assignment_drills"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("weekly_assignments.id", ondelete="CASCADE"), primary_key=True
    )
    drill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drills.id", ondelete="CASCADE"), primary_key=True
    )
    required_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    assignment: Mapped[WeeklyAssignment] = relationship(back_populates="items")
    drill: Mapped[Drill] = relationship(lazy="selectin")
