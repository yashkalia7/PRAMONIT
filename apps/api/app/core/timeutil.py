"""IST week arithmetic.

Every streak, weekly quota and leaderboard window in this app is bucketed by an
*Indian* week: Monday 00:00:00 IST through Sunday 23:59:59.999 IST.

Storage is always UTC (``timestamptz``). Bucketing is the only place the local
timezone appears, and it lives here alone so there is exactly one definition of
"which week is this?" in the codebase. Getting this wrong by one hour silently
misfiles every Sunday-evening upload, which is precisely when footballers train.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

try:  # pragma: no cover - platform dependent
    from zoneinfo import ZoneInfo

    IST = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover - Windows without tzdata installed
    # India has observed no DST since 1945, so a fixed offset is exact, not an
    # approximation. This keeps the app working even if tzdata is missing.
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Attach UTC to a naive datetime.

    SQLite has no timezone-aware column type, so values written as aware UTC come
    back naive. Comparing one of those against ``now_utc()`` raises
    ``TypeError: can't compare offset-naive and offset-aware datetimes``. Every
    datetime read from the database goes through here first.
    """
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def to_ist(dt: datetime) -> datetime:
    """Convert any datetime to IST. Naive input is assumed to be UTC."""
    return ensure_utc(dt).astimezone(IST)


def ist_date(dt: datetime) -> date:
    return to_ist(dt).date()


def week_start_for(dt: datetime) -> date:
    """The Monday (IST calendar date) of the week that ``dt`` falls in."""
    local = to_ist(dt).date()
    return local - timedelta(days=local.weekday())


def current_week_start() -> date:
    return week_start_for(now_utc())


def week_start_of_date(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_bounds_utc(week_start: date) -> tuple[datetime, datetime]:
    """Half-open UTC interval [start, end) covering an IST week.

    Half-open avoids the classic 23:59:59 gap that loses submissions landing in
    the final second of a week.
    """
    start_ist = datetime.combine(week_start, datetime.min.time(), tzinfo=IST)
    end_ist = start_ist + timedelta(days=7)
    return start_ist.astimezone(UTC), end_ist.astimezone(UTC)


def week_has_ended(week_start: date, at: datetime | None = None) -> bool:
    _, end_utc = week_bounds_utc(week_start)
    return (at or now_utc()) >= end_utc


def shift_weeks(week_start: date, delta: int) -> date:
    return week_start + timedelta(weeks=delta)


def weeks_between(earlier: date, later: date) -> int:
    """Whole weeks from one Monday to another. Negative if ``later`` precedes."""
    return (later - earlier).days // 7


def recent_week_starts(count: int, ending: date | None = None) -> list[date]:
    """``count`` Mondays, oldest first, ending at (and including) ``ending``."""
    last = ending or current_week_start()
    return [shift_weeks(last, -i) for i in range(count - 1, -1, -1)]


def label_for_week(week_start: date) -> str:
    """Human label, e.g. '11–17 Aug' or '28 Jul – 3 Aug'."""
    end = week_start + timedelta(days=6)
    if week_start.month == end.month:
        return f"{week_start.day}–{end.day} {end:%b}"
    return f"{week_start.day} {week_start:%b} – {end.day} {end:%b}"
