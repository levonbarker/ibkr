from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ibkr_trader.broker.market_data import YieldProvider
from ibkr_trader.broker.simulated import SimulatedBroker
from ibkr_trader.core.context import TradingContext
from ibkr_trader.core.intent import Instrument
from ibkr_trader.state.store import Store


def _ctx(broker: SimulatedBroker, store: Store) -> TradingContext:
    return TradingContext(
        broker=broker,
        accounts=broker.accounts(),
        now=datetime(2026, 10, 14, tzinfo=UTC),
        dry_run=True,
        yields=YieldProvider(broker, store),
    )


def test_fresh_fetch_is_persisted(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    broker = SimulatedBroker().set_yield("SGOV", Decimal("5.0"))
    provider = YieldProvider(broker, store)

    value = provider.get(Instrument("SGOV"), "ib_dividends")

    assert value == Decimal("5.0")
    assert store.get_yield("ib_dividends:SGOV.STK@SMART") is not None
    store.close()


def test_falls_back_to_cache_when_fetch_fails(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    store.put_yield("ib_dividends:SGOV.STK@SMART", Decimal("4.5"), "ib_dividends")
    broker = SimulatedBroker().set_yield("SGOV", None)  # fetch returns None

    value = YieldProvider(broker, store).get(Instrument("SGOV"), "ib_dividends")

    assert value == Decimal("4.5")
    store.close()


def test_returns_none_when_unknown_everywhere(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    broker = SimulatedBroker().set_yield("SGOV", None)

    assert YieldProvider(broker, store).get(Instrument("SGOV"), "ib_dividends") is None
    store.close()
