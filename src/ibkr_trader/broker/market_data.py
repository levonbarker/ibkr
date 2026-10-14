"""Yield discovery with a SQLite-backed cache.

Strategies ask for a yield and get either a fresh value, a cached fallback, or
``None``. ``None`` means "unknown" -- callers must never guess.
"""

from __future__ import annotations

from decimal import Decimal

from ibkr_trader.broker.base import Broker
from ibkr_trader.core.intent import Instrument
from ibkr_trader.state.store import Store
from ibkr_trader.util.logging import get_logger

log = get_logger("market_data")


class YieldProvider:
    def __init__(self, broker: Broker, store: Store) -> None:
        self.broker = broker
        self.store = store
        self._memo: dict[str, Decimal | None] = {}

    def get(self, instrument: Instrument, source: str) -> Decimal | None:
        key = f"{source}:{instrument.label}"
        if key in self._memo:
            return self._memo[key]

        value: Decimal | None = None
        try:
            if source == "fundamental":
                value = self.broker.fund_yield(instrument)
            else:
                value = self.broker.dividend_yield(instrument)
        except Exception as exc:  # noqa: BLE001
            log.warning("yield fetch failed for %s: %s", instrument.label, exc)

        if value is not None:
            self.store.put_yield(key, value, source)
        else:
            cached = self.store.get_yield(key)
            if cached is not None:
                log.info("using cached yield for %s (%s)", instrument.label, cached.source)
                value = cached.value

        self._memo[key] = value
        return value
