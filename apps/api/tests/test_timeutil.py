"""IST week bucketing.

This is the highest-leverage file in the suite. Every streak, quota and weekly
leaderboard depends on one question — "which week is this?" — and an error of a
single hour silently misfiles exactly the Sunday-evening uploads that footballers
actually make.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.timeutil import (
    IST,
    UTC,
    ensure_utc,
    ist_date,
    label_for_week,
    recent_week_starts,
    week_bounds_utc,
    week_has_ended,
    week_start_for,
    weeks_between,
)


def test_week_starts_on_monday_ist():
    # Wednesday 12 Aug 2026 IST -> week starting Monday 10 Aug
    dt = datetime(2026, 8, 12, 15, 0, tzinfo=IST)
    assert week_start_for(dt) == date(2026, 8, 10)


def test_sunday_night_and_monday_morning_are_different_weeks():
    """The boundary that breaks naive implementations."""
    sunday_late = datetime(2026, 8, 16, 23, 59, tzinfo=IST)
    monday_early = datetime(2026, 8, 17, 0, 1, tzinfo=IST)

    assert week_start_for(sunday_late) == date(2026, 8, 10)
    assert week_start_for(monday_early) == date(2026, 8, 17)
    assert week_start_for(sunday_late) != week_start_for(monday_early)


def test_utc_instant_near_midnight_ist_buckets_by_ist_not_utc():
    """18:30 UTC Sunday is already Monday in India.

    Bucketing on the UTC date would put this in the previous week and rob the
    student of the upload that started their new week.
    """
    instant = datetime(2026, 8, 16, 18, 31, tzinfo=UTC)  # = Mon 00:01 IST
    assert ist_date(instant) == date(2026, 8, 17)
    assert week_start_for(instant) == date(2026, 8, 17)


def test_utc_instant_just_before_ist_midnight_stays_in_old_week():
    instant = datetime(2026, 8, 16, 18, 29, tzinfo=UTC)  # = Sun 23:59 IST
    assert week_start_for(instant) == date(2026, 8, 10)


def test_naive_datetimes_are_treated_as_utc():
    """SQLite returns naive datetimes; they must not be read as local time."""
    naive = datetime(2026, 8, 16, 18, 31)
    assert week_start_for(naive) == date(2026, 8, 17)
    assert ensure_utc(naive).tzinfo is UTC


def test_week_bounds_are_half_open_and_cover_exactly_seven_days():
    start, end = week_bounds_utc(date(2026, 8, 10))
    assert end - start == timedelta(days=7)
    # 00:00 IST == 18:30 UTC the previous day
    assert start == datetime(2026, 8, 9, 18, 30, tzinfo=UTC)
    assert end == datetime(2026, 8, 16, 18, 30, tzinfo=UTC)


def test_week_bounds_leave_no_gap_between_consecutive_weeks():
    _, end_a = week_bounds_utc(date(2026, 8, 10))
    start_b, _ = week_bounds_utc(date(2026, 8, 17))
    assert end_a == start_b, "a submission in the seam would belong to no week"


def test_week_has_ended_uses_ist_midnight():
    week = date(2026, 8, 10)
    just_before = datetime(2026, 8, 16, 18, 29, tzinfo=UTC)
    just_after = datetime(2026, 8, 16, 18, 31, tzinfo=UTC)
    assert not week_has_ended(week, at=just_before)
    assert week_has_ended(week, at=just_after)


@pytest.mark.parametrize(
    "offset_hours",
    [0, 1, 5, 5.5, -8],
)
def test_bucketing_is_independent_of_the_server_timezone(offset_hours):
    """Same instant, expressed in different zones, must bucket identically."""
    instant = datetime(2026, 8, 16, 18, 31, tzinfo=UTC)
    shifted = instant.astimezone(timezone(timedelta(hours=offset_hours)))
    assert week_start_for(shifted) == week_start_for(instant) == date(2026, 8, 17)


def test_weeks_between_and_recent_weeks():
    assert weeks_between(date(2026, 8, 10), date(2026, 8, 31)) == 3
    weeks = recent_week_starts(4, ending=date(2026, 8, 31))
    assert weeks == [
        date(2026, 8, 10),
        date(2026, 8, 17),
        date(2026, 8, 24),
        date(2026, 8, 31),
    ]


def test_label_for_week_handles_month_rollover():
    assert label_for_week(date(2026, 8, 10)) == "10–16 Aug"
    assert label_for_week(date(2026, 7, 27)) == "27 Jul – 2 Aug"
