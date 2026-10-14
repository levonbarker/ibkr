"""Pre-trade guards.

Guards are pure predicates over an :class:`Intent`; they never mutate state or
talk to the broker. The engine runs every intent through the guard chain before
it is allowed near an order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ibkr_trader.core.context import TradingContext
from ibkr_trader.core.intent import Intent


@dataclass
class GuardConfig:
    kill_switch: bool = False
    allowed_symbols: set[str] = field(default_factory=set)
    max_order_usd: Decimal = Decimal("1000000")
    min_order_usd: Decimal = Decimal("1")


def intent_notional(intent: Intent) -> Decimal:
    """Best-effort notional for an intent (strategies set ``est_notional``)."""
    if intent.cash_quantity is not None:
        return abs(intent.cash_quantity)
    est = intent.meta.get("est_notional")
    if est is not None:
        return abs(Decimal(str(est)))
    return Decimal("0")


def check(intent: Intent, ctx: TradingContext, config: GuardConfig) -> str | None:
    """Return a skip/reject reason, or ``None`` when the intent is allowed."""

    if config.kill_switch:
        return "kill switch engaged"

    if config.allowed_symbols and intent.instrument.symbol not in config.allowed_symbols:
        return f"{intent.instrument.symbol} not in allowlist"

    notional = intent_notional(intent)
    if notional < config.min_order_usd:
        return f"notional {notional} below min_order_usd {config.min_order_usd}"
    if notional > config.max_order_usd:
        return f"notional {notional} above max_order_usd {config.max_order_usd}"

    return None
