"""The streak algorithm, exercised as a pure function.

The rules being pinned down here:

1. Consecutive weeks meeting the quota extend the streak.
2. The week in progress can only help — falling short mid-week breaks nothing.
3. A finished week that missed the quota ends the streak.
4. Unless videos from it are still awaiting review, in which case the streak is
   *held* (``provisional``) rather than cut — a coach's silence must never cost
   a student their record.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.timeutil import current_week_start, shift_weeks, week_has_ended
from app.models.progress import WeekResult
from app.services.streak import compute_streak_state

REQUIRED = 2


def wr(week_start, approved: int = 0, pending: int = 0) -> WeekResult:
    return WeekResult(
        student_id=uuid.uuid4(),
        week_start=week_start,
        approved_count=approved,
        pending_count=pending,
        rejected_count=0,
        required_count=REQUIRED,
        met=approved >= REQUIRED,
        finalised=week_has_ended(week_start) and pending == 0,
    )


def build(*specs) -> dict:
    """``build((-2, 2), (-1, 3))`` -> weeks at those offsets from the current one."""
    now = current_week_start()
    out = {}
    for offset, approved, *rest in specs:
        pending = rest[0] if rest else 0
        week = shift_weeks(now, offset)
        out[week] = wr(week, approved, pending)
    return out


def test_consecutive_met_weeks_accumulate():
    state = compute_streak_state(build((-3, 2), (-2, 2), (-1, 3), (0, 2)))
    assert state.current_weeks == 4
    assert state.provisional is False


def test_current_week_in_progress_does_not_break_the_streak():
    """Monday morning, nothing uploaded yet — the streak must survive."""
    state = compute_streak_state(build((-2, 2), (-1, 2), (0, 0)))
    assert state.current_weeks == 2


def test_partial_current_week_does_not_break_the_streak():
    state = compute_streak_state(build((-2, 2), (-1, 2), (0, 1)))
    assert state.current_weeks == 2


def test_missing_current_week_row_entirely_is_fine():
    state = compute_streak_state(build((-2, 2), (-1, 2)))
    assert state.current_weeks == 2


def test_finalised_unmet_week_breaks_the_streak():
    state = compute_streak_state(build((-3, 2), (-2, 1), (-1, 2), (0, 2)))
    # Only the current week and the one before it survive; -2 was short and is
    # settled, so the walk stops there.
    assert state.current_weeks == 2
    assert state.provisional is False


def test_ended_week_with_pending_review_holds_the_streak():
    """The coach-lag case: week ended 1/2 approved, 2 still queued."""
    state = compute_streak_state(build((-3, 2), (-2, 2), (-1, 1, 2), (0, 2)))
    assert state.current_weeks == 1, "only the current week counts until -1 resolves"
    assert state.provisional is True, "streak is held, not broken"


def test_pending_week_that_gets_approved_restores_the_streak():
    held = compute_streak_state(build((-2, 2), (-1, 1, 1), (0, 2)))
    assert held.provisional is True
    assert held.current_weeks == 1

    # The coach (or the 72h sweeper) approves the outstanding video.
    resolved = compute_streak_state(build((-2, 2), (-1, 2), (0, 2)))
    assert resolved.provisional is False
    assert resolved.current_weeks == 3


def test_pending_week_that_gets_rejected_breaks_the_streak():
    resolved = compute_streak_state(build((-2, 2), (-1, 1), (0, 2)))
    assert resolved.current_weeks == 1
    assert resolved.provisional is False


def test_no_history_is_zero_not_an_error():
    state = compute_streak_state({})
    assert state.current_weeks == 0
    assert state.longest_weeks == 0
    assert state.last_met_week is None


def test_longest_streak_survives_a_later_break():
    state = compute_streak_state(
        build((-6, 2), (-5, 2), (-4, 2), (-3, 0), (-2, 2), (-1, 2), (0, 2))
    )
    assert state.current_weeks == 3
    assert state.longest_weeks == 3


def test_longest_never_regresses_below_current():
    state = compute_streak_state(build((-1, 2), (0, 2)))
    assert state.longest_weeks >= state.current_weeks


def test_last_met_week_and_total_approved():
    now = current_week_start()
    state = compute_streak_state(build((-2, 2), (-1, 3), (0, 1)))
    assert state.last_met_week == shift_weeks(now, -1)
    assert state.total_approved == 6


@pytest.mark.parametrize("approved", [0, 1])
def test_below_quota_is_never_met(approved):
    state = compute_streak_state(build((-1, approved)))
    assert state.current_weeks == 0


@pytest.mark.parametrize("approved", [2, 3, 7])
def test_at_or_above_quota_is_met(approved):
    state = compute_streak_state(build((-1, approved)))
    assert state.current_weeks == 1
