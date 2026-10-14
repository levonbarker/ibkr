"""Execution context handed to strategies.

Strategies receive a :class:`TradingContext` and use it to read account state
without knowing how the broker is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ibkr_trader.broker.base import Broker, OpenOrder, Position
from ibkr_trader.broker.market_data import YieldProvider


@dataclass
class AccountSnapshot:
    account: str
    values: dict[str, Decimal]
    balances: dict[str, Decimal]
    positions: list[Position]
    open_orders: list[OpenOrder]

    def value(self, tag: str, default: Decimal = Decimal("0")) -> Decimal:
        return self.values.get(tag, default)

    def cash(self, currency: str = "USD") -> Decimal:
        return self.balances.get(currency, Decimal("0"))


@dataclass
class TradingContext:
    broker: Broker
    accounts: list[str]
    now: datetime
    dry_run: bool
    yields: YieldProvider
    _snapshots: dict[str, AccountSnapshot] = field(default_factory=dict, repr=False)

    def snapshot(self, account: str) -> AccountSnapshot:
        cached = self._snapshots.get(account)
        if cached is None:
            cached = AccountSnapshot(
                account=account,
                values=self.broker.account_values(account),
                balances=self.broker.account_currency_balances(account),
                positions=self.broker.positions(account),
                open_orders=self.broker.open_orders(account),
            )
            self._snapshots[account] = cached
        return cached
