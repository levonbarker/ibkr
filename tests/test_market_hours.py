from __future__ import annotations

from datetime import date, datetime

from ibkr_trader.util import market_hours as mh
from ibkr_trader.util.market_hours import EARLY_CLOSE, RTH_CLOSE


def test_weekends_closed():
    assert mh.is_trading_day(date(2026, 10, 17)) is False  # Saturday
    assert mh.is_trading_day(date(2026, 10, 18)) is False  # Sunday


def test_holidays_closed():
    assert mh.is_trading_day(date(2026, 7, 3)) is False  # observed July 4 (Fri)
    assert mh.is_trading_day(date(2026, 12, 25)) is False  # Christmas
    assert mh.is_trading_day(date(2026, 11, 26)) is False  # Thanksgiving


def test_regular_trading_day():
    assert mh.is_trading_day(date(2026, 10, 14)) is True


def test_early_close():
    # Day after Thanksgiving 2026 is Nov 27 (Fri) -> 13:00 close
    assert mh.close_time(date(2026, 11, 27)) == EARLY_CLOSE
    assert mh.close_time(date(2026, 10, 14)) == RTH_CLOSE


def test_is_rth_open():
    rth = datetime(2026, 10, 14, 11, 0, tzinfo=mh.NY)
    after = datetime(2026, 10, 14, 17, 0, tzinfo=mh.NY)
    weekend = datetime(2026, 10, 17, 11, 0, tzinfo=mh.NY)
    assert mh.is_rth_open(rth) is True
    assert mh.is_rth_open(after) is False
    assert mh.is_rth_open(weekend) is False
