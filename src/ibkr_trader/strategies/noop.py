"""A no-op strategy used to validate the framework end-to-end.

It plans nothing, but exercising it proves config loading, registry lookup,
strategy construction, and the run lifecycle all work.
"""

from __future__ import annotations

from ibkr_trader.core.context import TradingContext
from ibkr_trader.core.intent import Intent
from ibkr_trader.core.registry import register
from ibkr_trader.strategies.base import Strategy, StrategyConfig
from ibkr_trader.util.logging import get_logger

log = get_logger("strategy.noop")


@register
class NoopStrategy(Strategy):
    name = "noop"
    config_cls = StrategyConfig

    def enabled_accounts(self, ctx: TradingContext) -> list[str]:
        return ctx.accounts

    def plan(self, ctx: TradingContext, account: str) -> list[Intent]:
        log.info("noop strategy ran for %s (no orders)", account)
        return []
