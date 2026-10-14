"""Strategy contract.

A strategy is a **pure planner**: given an account snapshot it returns the
orders it wants to place. It never talks to the broker, never checks the clock,
and never transmits anything -- the engine owns all of that. This makes every
strategy trivially unit-testable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel

from ibkr_trader.core.context import TradingContext
from ibkr_trader.core.intent import Intent


class StrategyConfig(BaseModel):
    """Base class for per-strategy configuration models."""

    enabled: bool = True
    model_config = {"extra": "forbid"}


class Strategy(ABC):
    name: ClassVar[str] = ""
    config_cls: ClassVar[type[StrategyConfig]] = StrategyConfig

    def __init__(self, config: StrategyConfig, runtime: Any) -> None:
        self.config = config
        self.runtime = runtime

    @classmethod
    def build(cls, raw: dict[str, Any], runtime: Any) -> Strategy:
        return cls(cls.config_cls.model_validate(raw), runtime)

    @abstractmethod
    def enabled_accounts(self, ctx: TradingContext) -> list[str]:
        """Which accounts this strategy should run against this cycle."""

    @abstractmethod
    def plan(self, ctx: TradingContext, account: str) -> list[Intent]:
        """Return desired orders for ``account``. Must not perform IO."""
