"""Cash sweep: move idle cash into the best-yielding allowlisted product.

The strategy is a pure planner -- it inspects an account snapshot and returns
:class:`Intent` objects. All IO (yields, prices, order transmission) is exposed
through the context/broker, so this logic is fully unit-testable.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from typing import cast

from ibkr_trader.core.context import AccountSnapshot, TradingContext
from ibkr_trader.core.intent import Instrument, Intent
from ibkr_trader.core.registry import register
from ibkr_trader.strategies.base import Strategy
from ibkr_trader.strategies.cash_sweep.config import CashSweepConfig, UniverseEntry
from ibkr_trader.util.logging import get_logger

log = get_logger("strategy.cash_sweep")

_MMF = "MUTUALFUND"


@register
class CashSweepStrategy(Strategy):
    name = "cash_sweep"
    config_cls = CashSweepConfig

    @property
    def cfg(self) -> CashSweepConfig:
        return cast(CashSweepConfig, self.config)

    # -- planning -----------------------------------------------------------
    def enabled_accounts(self, ctx: TradingContext) -> list[str]:
        overrides = self.cfg.accounts
        if not overrides:
            return list(ctx.accounts)
        return [a for a in ctx.accounts if (ov := overrides.get(a)) is None or ov.enabled]

    def plan(self, ctx: TradingContext, account: str) -> list[Intent]:
        if not self.cfg.universe:
            log.warning("cash_sweep: empty universe, nothing to do")
            return []

        snapshot = ctx.snapshot(account)
        sweepable = self.sweepable_cash(snapshot)
        if sweepable < self.cfg.min_order_usd:
            log.info("cash_sweep[%s]: sweepable %.2f below minimum", account, sweepable)
            return []

        entry = self.select(snapshot, ctx)
        if entry is None:
            log.warning("cash_sweep[%s]: no eligible product with a known yield", account)
            return []

        instrument = Instrument(
            symbol=entry.symbol,
            sec_type=entry.sec_type,
            exchange=entry.exchange,
            currency=entry.currency,
        )
        return self._size(snapshot, ctx, account, instrument, entry, sweepable)

    def _size(
        self,
        snapshot: AccountSnapshot,
        ctx: TradingContext,
        account: str,
        instrument: Instrument,
        entry: UniverseEntry,
        sweepable: Decimal,
    ) -> list[Intent]:
        order_ref = f"cash_sweep:{ctx.now:%Y%m%d}:{account}:{instrument.symbol}"
        budget = min(sweepable, self.cfg.max_order_usd)

        if entry.sec_type == _MMF:
            return [
                Intent(
                    account=account,
                    instrument=instrument,
                    side="BUY",
                    strategy=self.name,
                    cash_quantity=budget,
                    order_ref=order_ref,
                    meta={"est_notional": str(budget), "source": entry.source},
                )
            ]

        price = ctx.broker.last_price(instrument)
        if not price or price <= 0:
            log.warning("cash_sweep[%s]: no price for %s", account, instrument.symbol)
            return []
        quantity = (budget / price).to_integral_value(rounding=ROUND_DOWN)
        notional = quantity * price
        if quantity <= 0 or notional < self.cfg.min_order_usd:
            log.info(
                "cash_sweep[%s]: %s notional %.2f below minimum",
                account,
                instrument.symbol,
                notional,
            )
            return []
        return [
            Intent(
                account=account,
                instrument=instrument,
                side="BUY",
                strategy=self.name,
                quantity=quantity,
                order_ref=order_ref,
                meta={
                    "est_notional": str(notional),
                    "price": str(price),
                    "source": entry.source,
                },
            )
        ]

    # -- helpers ------------------------------------------------------------
    def sweepable_cash(self, snapshot: AccountSnapshot) -> Decimal:
        balance = snapshot.cash()
        settled = snapshot.value("SettledCash", balance)
        available = min(balance, settled) if settled > 0 else balance
        return available - self.reserve_for(snapshot)

    def reserve_for(self, snapshot: AccountSnapshot) -> Decimal:
        reserve = self.cfg.reserve
        override = self.cfg.accounts.get(snapshot.account)
        if override and override.reserve_usd is not None:
            return override.reserve_usd

        percent_amount = snapshot.value("NetLiquidation") * reserve.percent / Decimal("100")
        if reserve.mode == "fixed":
            return reserve.fixed_usd
        if reserve.mode == "percent":
            return percent_amount
        return max(reserve.fixed_usd, percent_amount)

    def select(self, snapshot: AccountSnapshot, ctx: TradingContext) -> UniverseEntry | None:
        held = {p.instrument.symbol for p in snapshot.positions}
        scored: list[tuple[Decimal, int, int]] = []
        for idx, entry in enumerate(self.cfg.universe):
            if entry.currency != snapshot.base_currency:
                continue
            instrument = Instrument(
                symbol=entry.symbol,
                sec_type=entry.sec_type,
                exchange=entry.exchange,
                currency=entry.currency,
            )
            yld = ctx.yields.get(instrument, entry.source)
            if yld is None and entry.fallback_yield is not None:
                log.warning(
                    "cash_sweep: no live yield for %s, using configured fallback %s",
                    entry.symbol,
                    entry.fallback_yield,
                )
                yld = entry.fallback_yield
            if yld is None:
                log.info("cash_sweep: no yield for %s, ignoring", entry.symbol)
                continue
            tie = 1 if entry.symbol in held else 0
            scored.append((yld, tie, idx))

        if not scored:
            return None
        best = max(scored, key=lambda s: (s[0], s[1], -s[2]))
        return self.cfg.universe[best[2]]
