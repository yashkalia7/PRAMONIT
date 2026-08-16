"""Users, coach profiles and the verbose student profile."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_type, pk_uuid
from app.models.enums import DominantFoot, RosterStatus, UserRole


class User(Base, TimestampMixin):
    """Identity and credentials. Role decides which profile row hangs off it."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = pk_uuid()
    # Stored lower-cased at the application boundary so uniqueness is
    # case-insensitive without depending on the citext extension.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_type(UserRole, "user_role"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(24))
    dob: Mapped[date | None] = mapped_column(Date)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    coach_profile: Mapped["CoachProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    student_profile: Mapped["StudentProfile | None"] = relationship(
        foreign_keys="StudentProfile.user_id",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    coached_students: Mapped[list["StudentProfile"]] = relationship(
        foreign_keys="StudentProfile.coach_id", back_populates="coach"
    )

    @property
    def is_coach(self) -> bool:
        return self.role == UserRole.coach

    @property
    def is_student(self) -> bool:
        return self.role == UserRole.student

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User {self.role.value} {self.email}>"


class CoachProfile(Base, TimestampMixin):
    __tablename__ = "coach_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bio: Mapped[str | None] = mapped_column(Text)
    qualifications: Mapped[str | None] = mapped_column(Text)
    years_experience: Mapped[int | None] = mapped_column(Integer)
    specialization: Mapped[str | None] = mapped_column(String(120))
    primary_location: Mapped[str | None] = mapped_column(String(120))
    # JSON rather than ARRAY: Postgres arrays have no SQLite equivalent, and the
    # list is only ever read/written wholesale.
    batches: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    user: Mapped[User] = relationship(back_populates="coach_profile")


class StudentProfile(Base, TimestampMixin):
    """Deliberately verbose — v0 collects broadly so later phases can narrow.

    ``batch_name`` and ``course`` are free text on purpose: the club is still
    deciding its taxonomy, and a lookup table would have to be migrated every
    time a new batch opens.
    """

    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    coach_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    roster_status: Mapped[RosterStatus] = mapped_column(
        enum_type(RosterStatus, "roster_status"), default=RosterStatus.active, nullable=False
    )

    batch_name: Mapped[str | None] = mapped_column(String(120), index=True)
    course: Mapped[str | None] = mapped_column(String(120))

    jersey_number: Mapped[int | None] = mapped_column(Integer)
    preferred_position: Mapped[str | None] = mapped_column(String(60))
    dominant_foot: Mapped[DominantFoot | None] = mapped_column(
        enum_type(DominantFoot, "dominant_foot")
    )
    height_cm: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2))
    years_playing: Mapped[int | None] = mapped_column(Integer)
    previous_club: Mapped[str | None] = mapped_column(String(120))
    school_name: Mapped[str | None] = mapped_column(String(160))

    guardian_name: Mapped[str | None] = mapped_column(String(120))
    guardian_phone: Mapped[str | None] = mapped_column(String(24))
    guardian_email: Mapped[str | None] = mapped_column(String(255))
    emergency_contact: Mapped[str | None] = mapped_column(String(160))
    medical_notes: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)

    joined_at: Mapped[date | None] = mapped_column(Date)
    consent_media: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="student_profile")
    coach: Mapped[User | None] = relationship(
        foreign_keys=[coach_id], back_populates="coached_students"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<StudentProfile {self.user_id} batch={self.batch_name!r}>"
