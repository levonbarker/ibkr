from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ibkr_trader.broker.market_data import YieldProvider
from ibkr_trader.broker.simulated import SimulatedBroker
from ibkr_trader.core.context import TradingContext
from ibkr_trader.state.store import Store


@pytest.fixture
def broker() -> SimulatedBroker:
    return SimulatedBroker()


@pytest.fixture
def store(tmp_path) -> Store:
    s = Store(tmp_path / "test.sqlite3")
    yield s
    s.close()


@pytest.fixture
def ctx(broker: SimulatedBroker, store: Store) -> TradingContext:
    return TradingContext(
        broker=broker,
        accounts=broker.accounts(),
        now=datetime(2026, 10, 14, 15, 0, tzinfo=UTC),
        dry_run=True,
        yields=YieldProvider(broker, store),
    )
