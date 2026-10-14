"""Configuration model for the cash sweep strategy."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from ibkr_trader.strategies.base import StrategyConfig


class ReserveConfig(BaseModel):
    """How much cash to leave un-swept in each account."""

    mode: Literal["fixed", "percent", "max"] = "fixed"
    fixed_usd: Decimal = Decimal("5000")
    percent: Decimal = Decimal("0")  # percent of net liquidation value
    model_config = {"extra": "forbid"}


class AccountOverride(BaseModel):
    enabled: bool = True
    reserve_usd: Decimal | None = None
    model_config = {"extra": "forbid"}


class UniverseEntry(BaseModel):
    symbol: str
    sec_type: str = "STK"
    exchange: str = "SMART"
    currency: str = "USD"
    source: Literal["ib_dividends", "fundamental"] = "ib_dividends"
    model_config = {"extra": "forbid"}


class CashSweepConfig(StrategyConfig):
    accounts: dict[str, AccountOverride] = Field(default_factory=dict)
    reserve: ReserveConfig = Field(default_factory=ReserveConfig)
    min_order_usd: Decimal = Decimal("100")
    max_order_usd: Decimal = Decimal("250000")
    universe: list[UniverseEntry] = Field(default_factory=list)
