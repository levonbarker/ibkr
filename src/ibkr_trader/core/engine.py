"""The engine: connect -> plan -> guard -> execute -> record.

All broker IO, safety checks, idempotency and persistence live here. Strategies
only ever produce :class:`Intent` objects.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ibkr_trader.broker.base import Broker
from ibkr_trader.broker.market_data import YieldProvider
from ibkr_trader.core import registry
from ibkr_trader.core.config import AppConfig
from ibkr_trader.core.context import TradingContext
from ibkr_trader.core.intent import Intent, Result
from ibkr_trader.state.store import Store
from ibkr_trader.util import guards
from ibkr_trader.util.logging import get_logger
from ibkr_trader.util.notify import Notifier

log = get_logger("engine")


class Engine:
    def __init__(
        self,
        config: AppConfig,
        broker: Broker,
        store: Store,
        notifier: Notifier | None = None,
    ) -> None:
        self.config = config
        self.broker = broker
        self.store = store
        self.notifier = notifier or Notifier()

    def run(self) -> list[Result]:
        accounts = self._resolve_accounts()
        now = datetime.now(ZoneInfo(self.config.runtime.timezone))
        ctx = TradingContext(
            broker=self.broker,
            accounts=accounts,
            now=now,
            dry_run=self.config.runtime.dry_run,
            yields=YieldProvider(self.broker, self.store),
        )
        guard_config = guards.GuardConfig(
            kill_switch=self.config.runtime.guards.kill_switch,
            allowed_symbols=set(self.config.runtime.guards.allowed_symbols),
            max_order_usd=self.config.runtime.guards.max_order_usd,
            min_order_usd=self.config.runtime.guards.min_order_usd,
        )

        run_id = self.store.start_run(accounts, ctx.dry_run)
        self.notifier.run_started(accounts, ctx.dry_run)
        results: list[Result] = []
        try:
            for name, block in self.config.enabled_strategies().items():
                try:
                    strategy = registry.get(name).build(block, self.config.runtime)
                except Exception as exc:  # noqa: BLE001 - isolate bad strategies
                    log.error("strategy %r failed to load: %s", name, exc)
                    continue
                for account in strategy.enabled_accounts(ctx):
                    try:
                        intents = strategy.plan(ctx, account)
                    except Exception as exc:  # noqa: BLE001
                        log.error("strategy %r plan failed for %s: %s", name, account, exc)
                        continue
                    results.extend(
                        self._execute(run_id, ctx, intent, guard_config) for intent in intents
                    )
        finally:
            self.store.finish_run(run_id)

        self.notifier.run_finished(results)
        return results

    def _execute(
        self,
        run_id: int,
        ctx: TradingContext,
        intent: Intent,
        guard_config: guards.GuardConfig,
    ) -> Result:
        reason = guards.check(intent, ctx, guard_config)
        if reason:
            return self._record(run_id, intent, Result(intent, "SKIPPED", reason))

        if self.store.seen_order_ref(intent.order_ref):
            return self._record(run_id, intent, Result(intent, "SKIPPED", "duplicate order_ref"))

        if ctx.dry_run:
            return self._record(run_id, intent, Result(intent, "DRY_RUN", "dry-run"))

        result = self.broker.place_order(intent)
        return self._record(run_id, intent, result)

    def _record(self, run_id: int, intent: Intent, result: Result) -> Result:
        self.store.record(run_id, intent, result)
        return result

    def _resolve_accounts(self) -> list[str]:
        available = self.broker.accounts()
        configured = self.config.runtime.accounts
        if not configured:
            return available
        return [a for a, setting in configured.items() if setting.enabled and a in available]
