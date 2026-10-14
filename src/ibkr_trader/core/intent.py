"""Pure data types that flow through the engine pipeline.

Strategies emit :class:`Intent` objects (what they *want* to do); the engine
turns those into :class:`Result` objects (what actually happened). Keeping these
free of broker/IO types is what makes strategies unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class Instrument:
    """A broker-agnostic description of a tradable instrument."""

    symbol: str
    sec_type: str = "STK"
    exchange: str = "SMART"
    currency: str = "USD"
    primary_exchange: str = ""
    con_id: int = 0

    @property
    def label(self) -> str:
        return f"{self.symbol}.{self.sec_type}@{self.exchange or 'SMART'}"


@dataclass(frozen=True)
class Intent:
    """A desired order, produced by a strategy and consumed by the engine.

    Exactly one of ``quantity`` or ``cash_quantity`` must be set. Mutual funds
    use ``cash_quantity`` (dollar-based orders); equities/ETFs use ``quantity``.
    """

    account: str
    instrument: Instrument
    side: Side
    strategy: str
    quantity: Decimal | None = None
    cash_quantity: Decimal | None = None
    order_type: str = "MKT"
    limit_price: Decimal | None = None
    # Stable, human-readable key used for idempotency and audit.
    order_ref: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (self.quantity is None) == (self.cash_quantity is None):
            raise ValueError("Intent requires exactly one of quantity / cash_quantity")


@dataclass
class Result:
    """Outcome of attempting to execute an :class:`Intent`."""

    intent: Intent
    status: Literal["DRY_RUN", "SUBMITTED", "SKIPPED", "REJECTED", "ERROR"]
    message: str = ""
    order_id: int | None = None
    broker_status: str = ""
    filled_quantity: Decimal | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def ok(self) -> bool:
        return self.status in ("DRY_RUN", "SUBMITTED")
