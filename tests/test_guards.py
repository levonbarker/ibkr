from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ibkr_trader.broker.market_data import YieldProvider
from ibkr_trader.broker.simulated import SimulatedBroker
from ibkr_trader.core.context import TradingContext
from ibkr_trader.core.intent import Instrument, Intent
from ibkr_trader.state.store import Store
from ibkr_trader.util import guards


def _ctx(broker: SimulatedBroker, store: Store) -> TradingContext:
    return TradingContext(
        broker=broker,
        accounts=broker.accounts(),
        now=datetime(2026, 10, 14, tzinfo=UTC),
        dry_run=True,
        yields=YieldProvider(broker, store),
    )


def _intent(**kw) -> Intent:
    base = dict(
        account="DU1",
        instrument=Instrument("SGOV"),
        side="BUY",
        strategy="test",
        cash_quantity=Decimal("5000"),
        order_ref="ref",
    )
    base.update(kw)
    return Intent(**base)


def test_kill_switch():
    cfg = guards.GuardConfig(kill_switch=True)
    assert guards.check(_intent(), None, cfg) == "kill switch engaged"  # type: ignore[arg-type]


def test_allowlist():
    cfg = guards.GuardConfig(allowed_symbols={"BIL"})
    assert "not in allowlist" in (guards.check(_intent(), None, cfg) or "")  # type: ignore[arg-type]


def test_min_and_max_notional():
    cfg = guards.GuardConfig(min_order_usd=Decimal("10000"))
    assert "below min" in (guards.check(_intent(), None, cfg) or "")  # type: ignore[arg-type]

    cfg = guards.GuardConfig(max_order_usd=Decimal("100"))
    assert "above max" in (guards.check(_intent(), None, cfg) or "")  # type: ignore[arg-type]


def test_passes_when_clean():
    cfg = guards.GuardConfig(max_order_usd=Decimal("100000"))
    assert guards.check(_intent(), None, cfg) is None  # type: ignore[arg-type]


def test_intent_requires_exactly_one_size():
    import pytest

    with pytest.raises(ValueError):
        Intent(
            account="DU1",
            instrument=Instrument("SGOV"),
            side="BUY",
            strategy="test",
            order_ref="x",
        )
