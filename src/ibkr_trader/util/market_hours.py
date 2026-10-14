"""US equity market calendar (NYSE hours), dependency-free.

Covers trading days, regular hours, and the standard 13:00 ET early closes.
Good enough for scheduling sweeps; not a substitute for a full calendar.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)
EARLY_CLOSE = time(13, 0)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """``n``-th ``weekday`` (Mon=0) of a month; ``n=-1`` for the last one."""
    if n > 0:
        first = date(year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + timedelta(days=offset + 7 * (n - 1))
    if n == -1:
        last_day = date(year, month, 1) + timedelta(days=32)
        last = date(last_day.year, last_day.month, 1) - timedelta(days=1)
        offset = (last.weekday() - weekday) % 7
        return last - timedelta(days=offset)
    raise ValueError("n must be positive or -1")


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _easter(year: int) -> date:
    """Anonymous Gregorian computus."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    p = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * p) // 451
    month, day = divmod(h + p - 7 * m + 114, 31)
    return date(year, month, day + 1)


def holidays(year: int) -> set[date]:
    return {
        _observed(date(year, 1, 1)),  # New Year's Day
        _nth_weekday(year, 1, 0, 3),  # MLK Day
        _nth_weekday(year, 2, 0, 3),  # Presidents' Day
        _easter(year) - timedelta(days=2),  # Good Friday
        _nth_weekday(year, 5, 0, -1),  # Memorial Day
        _observed(date(year, 6, 19)),  # Juneteenth
        _observed(date(year, 7, 4)),  # Independence Day
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed(date(year, 12, 25)),  # Christmas
    }


def is_trading_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    return day not in holidays(day.year)


def early_closes(year: int) -> set[date]:
    result: set[date] = set()
    july3 = date(year, 7, 3)
    if july3.weekday() < 5 and july3 not in holidays(year):
        result.add(july3)
    result.add(_nth_weekday(year, 11, 3, 4) + timedelta(days=1))  # day after Thanksgiving
    dec24 = date(year, 12, 24)
    if dec24.weekday() < 5:
        result.add(dec24)
    return result


def close_time(day: date) -> time:
    """Regular close, accounting for the standard early-close days."""
    return EARLY_CLOSE if day in early_closes(day.year) else RTH_CLOSE


def is_rth_open(now: datetime | None = None) -> bool:
    now = now.astimezone(NY) if now else datetime.now(NY)
    if not is_trading_day(now.date()):
        return False
    return RTH_OPEN <= now.time() < close_time(now.date())
