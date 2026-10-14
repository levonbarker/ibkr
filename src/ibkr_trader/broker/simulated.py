"""In-memory broker used for tests and offline dry-runs.

Lets the whole pipeline be exercised without a Gateway, network, or ib_async.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ibkr_trader.broker.base import OpenOrder, Position
from ibkr_trader.core.intent import Instrument, Intent, Result


@dataclass
class SimulatedBroker:
    _accounts: list[str] = field(default_factory=lambda: ["DU1111111"])
    _values: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    _balances: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    _positions: dict[str, list[Position]] = field(default_factory=dict)
    _open_orders: dict[str, list[OpenOrder]] = field(default_factory=dict)
    _yields: dict[str, Decimal | None] = field(default_factory=dict)
    _prices: dict[str, Decimal] = field(default_factory=dict)
    _base_currency: dict[str, str] = field(default_factory=dict)
    placed: list[Intent] = field(default_factory=list)
    connected: bool = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def accounts(self) -> list[str]:
        return list(self._accounts)

    def base_currency(self, account: str) -> str:
        return self._base_currency.get(account, "USD")

    def account_values(self, account: str) -> dict[str, Decimal]:
        return dict(self._values.get(account, {}))

    def account_currency_balances(self, account: str) -> dict[str, Decimal]:
        return dict(self._balances.get(account, {}))

    def positions(self, account: str) -> list[Position]:
        return list(self._positions.get(account, []))

    def open_orders(self, account: str) -> list[OpenOrder]:
        return list(self._open_orders.get(account, []))

    def qualify(self, instrument: Instrument) -> Instrument:
        return instrument

    def place_order(self, intent: Intent) -> Result:
        self.placed.append(intent)
        return Result(
            intent=intent,
            status="SUBMITTED",
            message="simulated",
            order_id=len(self.placed),
            broker_status="Filled",
        )

    def dividend_yield(self, instrument: Instrument) -> Decimal | None:
        return self._yields.get(instrument.symbol)

    def fund_yield(self, instrument: Instrument) -> Decimal | None:
        return self._yields.get(instrument.symbol)

    def last_price(self, instrument: Instrument) -> Decimal | None:
        return self._prices.get(instrument.symbol)

    # -- test helpers -------------------------------------------------------
    def set_cash(self, account: str, usd: Decimal) -> SimulatedBroker:
        self._balances.setdefault(account, {})["USD"] = Decimal(usd)
        self._values.setdefault(account, {}).setdefault("SettledCash", Decimal(usd))
        return self

    def set_value(self, account: str, tag: str, value: Decimal) -> SimulatedBroker:
        self._values.setdefault(account, {})[tag] = Decimal(value)
        return self

    def set_yield(self, symbol: str, value: Decimal | None) -> SimulatedBroker:
        self._yields[symbol] = value
        return self

    def set_price(self, symbol: str, value: Decimal) -> SimulatedBroker:
        self._prices[symbol] = Decimal(value)
        return self

    def set_base_currency(self, account: str, currency: str) -> SimulatedBroker:
        self._base_currency[account] = currency
        return self

    def set_balance(self, account: str, currency: str, amount: Decimal) -> SimulatedBroker:
        self._balances.setdefault(account, {})[currency] = Decimal(amount)
        return self

    def add_position(
        self, account: str, instrument: Instrument, qty: Decimal, cost: Decimal
    ) -> None:
        self._positions.setdefault(account, []).append(
            Position(account=account, instrument=instrument, quantity=qty, average_cost=cost)
        )


def demo_broker(account: str = "DU1111111") -> SimulatedBroker:
    """A ready-to-run broker for offline demos / `--simulate`."""
    return (
        SimulatedBroker(_accounts=[account])
        .set_cash(account, Decimal("10000"))
        .set_value(account, "NetLiquidation", Decimal("100000"))
        .set_value(account, "SettledCash", Decimal("10000"))
        .set_yield("SGOV", Decimal("5.15"))
        .set_yield("BIL", Decimal("4.90"))
        .set_price("SGOV", Decimal("100.25"))
        .set_price("BIL", Decimal("91.40"))
    )
