"""Auth and registration payloads.

Student registration is intentionally verbose: v0 collects broadly so later
phases can narrow down to what actually gets used, rather than discovering six
months in that nobody recorded who to call when a child is injured.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import DominantFoot, RosterStatus, UserRole

PASSWORD_MIN = 8


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class _RegisterBase(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=24)
    dob: date | None = None

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("full_name")
    @classmethod
    def _trim(cls, v: str) -> str:
        return " ".join(v.split())


class CoachRegisterRequest(_RegisterBase):
    bio: str | None = None
    qualifications: str | None = None
    years_experience: int | None = Field(default=None, ge=0, le=70)
    specialization: str | None = Field(default=None, max_length=120)
    primary_location: str | None = Field(default=None, max_length=120)
    batches: list[str] = Field(default_factory=list)


class StudentRegisterRequest(_RegisterBase):
    coach_id: uuid.UUID

    # Free text on purpose — the club's batch taxonomy is still forming, and a
    # lookup table would need migrating every time a new slot opens.
    batch_name: str | None = Field(default=None, max_length=120)
    course: str | None = Field(default=None, max_length=120)

    jersey_number: int | None = Field(default=None, ge=0, le=99)
    preferred_position: str | None = Field(default=None, max_length=60)
    dominant_foot: DominantFoot | None = None
    height_cm: int | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=10, le=200)
    years_playing: int | None = Field(default=None, ge=0, le=40)
    previous_club: str | None = Field(default=None, max_length=120)
    school_name: str | None = Field(default=None, max_length=160)

    guardian_name: str | None = Field(default=None, max_length=120)
    guardian_phone: str | None = Field(default=None, max_length=24)
    guardian_email: EmailStr | None = None
    emergency_contact: str | None = Field(default=None, max_length=160)
    medical_notes: str | None = None
    address: str | None = None
    consent_media: bool = False


class CoachPublic(_Base):
    """What an unauthenticated signup screen is allowed to see."""

    id: uuid.UUID
    full_name: str
    specialization: str | None = None
    primary_location: str | None = None
    batches: list[str] = Field(default_factory=list)
    student_count: int = 0


class CoachProfileOut(_Base):
    bio: str | None = None
    qualifications: str | None = None
    years_experience: int | None = None
    specialization: str | None = None
    primary_location: str | None = None
    batches: list[str] = Field(default_factory=list)


class StudentProfileOut(_Base):
    coach_id: uuid.UUID | None = None
    coach_name: str | None = None
    roster_status: RosterStatus = RosterStatus.active
    batch_name: str | None = None
    course: str | None = None
    jersey_number: int | None = None
    preferred_position: str | None = None
    dominant_foot: DominantFoot | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    years_playing: int | None = None
    previous_club: str | None = None
    school_name: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    emergency_contact: str | None = None
    medical_notes: str | None = None
    address: str | None = None
    joined_at: date | None = None
    consent_media: bool = False


class UserOut(_Base):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    full_name: str
    phone: str | None = None
    dob: date | None = None
    avatar_url: str | None = None


class MeOut(UserOut):
    coach_profile: CoachProfileOut | None = None
    student_profile: StudentProfileOut | None = None


class AuthResponse(BaseModel):
    tokens: TokenPair
    user: MeOut
