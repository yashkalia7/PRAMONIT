"""Shared FastAPI dependencies: authentication and role gates."""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    try:
        # expected_type="access" matters: without it a 30-day refresh token
        # would authorise ordinary API calls for its whole lifetime.
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise CREDENTIALS_ERROR from exc

    user = (
        await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.coach_profile),
                selectinload(User.student_profile),
            )
        )
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_coach(user: CurrentUser) -> User:
    if user.role != UserRole.coach:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Coach access required"
        )
    return user


async def require_student(user: CurrentUser) -> User:
    if user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student access required"
        )
    return user


CoachUser = Annotated[User, Depends(require_coach)]
StudentUser = Annotated[User, Depends(require_student)]


async def get_optional_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User | None:
    if credentials is None:
        return None
    try:
        return await get_current_user(session, credentials)
    except HTTPException:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
