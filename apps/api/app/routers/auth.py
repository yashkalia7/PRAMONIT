"""Registration, login and token refresh."""

from __future__ import annotations

import uuid
from datetime import date

import jwt
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_expiry_seconds,
    verify_password,
)
from app.models.enums import RosterStatus, UserRole
from app.models.user import CoachProfile, StudentProfile, User
from app.schemas.auth import (
    AuthResponse,
    CoachPublic,
    CoachProfileOut,
    CoachRegisterRequest,
    LoginRequest,
    MeOut,
    RefreshRequest,
    StudentProfileOut,
    StudentRegisterRequest,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])
public_router = APIRouter(prefix="/public", tags=["public"])


def _tokens_for(user: User) -> TokenPair:
    subject = str(user.id)
    return TokenPair(
        access_token=create_access_token(subject, user.role.value),
        refresh_token=create_refresh_token(subject, user.role.value),
        expires_in=token_expiry_seconds(),
    )


async def _serialise_me(session, user: User) -> MeOut:
    coach_out = None
    student_out = None

    if user.coach_profile is not None:
        coach_out = CoachProfileOut.model_validate(user.coach_profile)

    if user.student_profile is not None:
        profile = user.student_profile
        student_out = StudentProfileOut.model_validate(profile)
        if profile.coach_id:
            student_out.coach_name = (
                await session.execute(
                    select(User.full_name).where(User.id == profile.coach_id)
                )
            ).scalar_one_or_none()

    data = MeOut.model_validate(user)
    data.coach_profile = coach_out
    data.student_profile = student_out
    return data


async def _load_user(session, user_id: uuid.UUID) -> User | None:
    return (
        await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.coach_profile),
                selectinload(User.student_profile),
            )
        )
    ).scalar_one_or_none()


@router.post("/register/coach", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_coach(payload: CoachRegisterRequest, session: DbSession) -> AuthResponse:
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.coach,
        full_name=payload.full_name,
        phone=payload.phone,
        dob=payload.dob,
    )
    user.coach_profile = CoachProfile(
        bio=payload.bio,
        qualifications=payload.qualifications,
        years_experience=payload.years_experience,
        specialization=payload.specialization,
        primary_location=payload.primary_location,
        batches=payload.batches or [],
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="That email is already registered"
        ) from exc

    fresh = await _load_user(session, user.id)
    return AuthResponse(tokens=_tokens_for(fresh), user=await _serialise_me(session, fresh))


@router.post(
    "/register/student", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register_student(payload: StudentRegisterRequest, session: DbSession) -> AuthResponse:
    coach = (
        await session.execute(
            select(User).where(User.id == payload.coach_id, User.role == UserRole.coach)
        )
    ).scalar_one_or_none()
    if coach is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Selected coach does not exist"
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.student,
        full_name=payload.full_name,
        phone=payload.phone,
        dob=payload.dob,
    )
    user.student_profile = StudentProfile(
        coach_id=coach.id,
        roster_status=RosterStatus.active,
        batch_name=payload.batch_name,
        course=payload.course,
        jersey_number=payload.jersey_number,
        preferred_position=payload.preferred_position,
        dominant_foot=payload.dominant_foot,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        years_playing=payload.years_playing,
        previous_club=payload.previous_club,
        school_name=payload.school_name,
        guardian_name=payload.guardian_name,
        guardian_phone=payload.guardian_phone,
        guardian_email=payload.guardian_email,
        emergency_contact=payload.emergency_contact,
        medical_notes=payload.medical_notes,
        address=payload.address,
        consent_media=payload.consent_media,
        joined_at=date.today(),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="That email is already registered"
        ) from exc

    fresh = await _load_user(session, user.id)
    return AuthResponse(tokens=_tokens_for(fresh), user=await _serialise_me(session, fresh))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, session: DbSession) -> AuthResponse:
    user = (
        await session.execute(
            select(User)
            .where(User.email == payload.email)
            .options(
                selectinload(User.coach_profile),
                selectinload(User.student_profile),
            )
        )
    ).scalar_one_or_none()

    # Same message and same work for "no such user" and "wrong password" so the
    # endpoint cannot be used to enumerate who has an account.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated"
        )

    return AuthResponse(tokens=_tokens_for(user), user=await _serialise_me(session, user))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return _tokens_for(user)


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser, session: DbSession) -> MeOut:
    return await _serialise_me(session, user)


@public_router.get("/coaches", response_model=list[CoachPublic])
async def list_coaches(session: DbSession) -> list[CoachPublic]:
    """Populates the coach dropdown on the student signup screen.

    Unauthenticated by necessity — the student has no account yet. It therefore
    exposes only what a prospective student needs to choose: name, speciality,
    location, batches and roster size. No contact details.
    """
    counts = dict(
        (
            await session.execute(
                select(StudentProfile.coach_id, func.count())
                .where(StudentProfile.roster_status == RosterStatus.active)
                .group_by(StudentProfile.coach_id)
            )
        ).all()
    )

    coaches = (
        await session.execute(
            select(User)
            .where(User.role == UserRole.coach, User.is_active.is_(True))
            .options(selectinload(User.coach_profile))
            .order_by(User.full_name)
        )
    ).scalars().all()

    return [
        CoachPublic(
            id=coach.id,
            full_name=coach.full_name,
            specialization=coach.coach_profile.specialization if coach.coach_profile else None,
            primary_location=(
                coach.coach_profile.primary_location if coach.coach_profile else None
            ),
            batches=coach.coach_profile.batches if coach.coach_profile else [],
            student_count=counts.get(coach.id, 0),
        )
        for coach in coaches
    ]
