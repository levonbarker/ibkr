"""Broker abstraction.

The engine talks to a :class:`Broker` and never to ``ib_async`` directly. This
keeps the orchestration testable (a simulated broker is trivial to provide) and
confines all IB-specific quirks to :mod:`ibkr_trader.broker.ibkr`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from ibkr_trader.core.intent import Instrument, Result
from ibkr_trader.core.intent import Intent as OrderIntent


@dataclass(frozen=True)
class Position:
    account: str
    instrument: Instrument
    quantity: Decimal
    average_cost: Decimal


@dataclass(frozen=True)
class OpenOrder:
    account: str
    order_ref: str
    instrument: Instrument
    side: str
    status: str


@runtime_checkable
class Broker(Protocol):
    """Minimal surface the engine and strategies depend on."""

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def accounts(self) -> list[str]: ...

    def account_values(self, account: str) -> dict[str, Decimal]: ...

    def account_currency_balances(self, account: str) -> dict[str, Decimal]: ...

    def positions(self, account: str) -> list[Position]: ...

    def open_orders(self, account: str) -> list[OpenOrder]: ...

    def qualify(self, instrument: Instrument) -> Instrument: ...

    def place_order(self, intent: OrderIntent) -> Result: ...

    # Market-data helpers used by sizing and yield discovery.
    def last_price(self, instrument: Instrument) -> Decimal | None: ...

    def dividend_yield(self, instrument: Instrument) -> Decimal | None: ...

    def fund_yield(self, instrument: Instrument) -> Decimal | None: ...
