"""Leaderboard endpoint — three scopes, two windows."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.models.enums import LeaderboardScope, LeaderboardWindow, UserRole
from app.schemas.progress import LeaderboardOut, LeaderboardRowOut
from app.services.leaderboard import build_leaderboard

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=LeaderboardOut)
async def leaderboard(
    session: DbSession,
    user: CurrentUser,
    scope: LeaderboardScope = Query(default=LeaderboardScope.batch),
    window: LeaderboardWindow = Query(default=LeaderboardWindow.week),
    batch: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> LeaderboardOut:
    viewer_id = user.id if user.role == UserRole.student else None
    coach_id = user.id if user.role == UserRole.coach else None

    if user.role == UserRole.coach and scope == LeaderboardScope.batch and not batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coaches must name a batch for the batch scope",
        )

    page = await build_leaderboard(
        session,
        scope=scope,
        window=window,
        viewer_id=viewer_id,
        coach_id=coach_id,
        batch_name=batch,
        limit=limit,
    )

    return LeaderboardOut(
        scope=page.scope,
        window=page.window,
        week_start=page.week_start,
        total_students=page.total_students,
        # asdict, not vars: LeaderboardRow is a slots dataclass and has no __dict__.
        rows=[LeaderboardRowOut(**asdict(row)) for row in page.rows],
        viewer_row=LeaderboardRowOut(**asdict(page.viewer_row)) if page.viewer_row else None,
    )
