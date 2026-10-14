from __future__ import annotations

from decimal import Decimal

from ibkr_trader.broker.simulated import SimulatedBroker
from ibkr_trader.core.context import TradingContext
from ibkr_trader.strategies.cash_sweep.config import CashSweepConfig
from ibkr_trader.strategies.cash_sweep.strategy import CashSweepStrategy

ACCOUNT = "DU1111111"


def _strategy(ctx: TradingContext, **overrides) -> CashSweepStrategy:
    raw = {
        "reserve": {"mode": "fixed", "fixed_usd": 5000},
        "min_order_usd": 100,
        "max_order_usd": 250000,
        "universe": [
            {"symbol": "SGOV", "sec_type": "STK", "source": "ib_dividends"},
            {"symbol": "BIL", "sec_type": "STK", "source": "ib_dividends"},
        ],
    }
    raw.update(overrides)
    return CashSweepStrategy(CashSweepConfig.model_validate(raw), runtime=None)


def test_sweeps_cash_into_best_yield_etf(ctx, broker: SimulatedBroker):
    broker.set_cash(ACCOUNT, Decimal("10000")).set_value(
        ACCOUNT, "NetLiquidation", Decimal("100000")
    )
    broker.set_yield("SGOV", Decimal("5.0")).set_yield("BIL", Decimal("4.8"))
    broker.set_price("SGOV", Decimal("100")).set_price("BIL", Decimal("91"))

    strategy = _strategy(ctx)
    intents = strategy.plan(ctx, ACCOUNT)

    assert len(intents) == 1
    intent = intents[0]
    assert intent.instrument.symbol == "SGOV"  # highest yield wins
    assert intent.side == "BUY"
    assert intent.quantity == Decimal("50")  # (10000 - 5000) / 100
    assert intent.meta["est_notional"] == "5000"
    assert intent.order_ref == f"cash_sweep:20261014:{ACCOUNT}:SGOV"


def test_reserve_percent_mode(ctx, broker: SimulatedBroker):
    broker.set_cash(ACCOUNT, Decimal("50000")).set_value(
        ACCOUNT, "NetLiquidation", Decimal("100000")
    )
    broker.set_yield("SGOV", Decimal("5.0")).set_price("SGOV", Decimal("100"))

    strategy = _strategy(ctx, reserve={"mode": "percent", "percent": 10})
    intents = strategy.plan(ctx, ACCOUNT)

    assert intents[0].quantity == Decimal("400")  # (50000 - 10000) / 100


def test_money_market_fund_uses_cash_quantity(ctx, broker: SimulatedBroker):
    broker.set_cash(ACCOUNT, Decimal("8000")).set_value(ACCOUNT, "NetLiquidation", Decimal("8000"))
    broker.set_yield("VMFXX", Decimal("5.2"))

    strategy = _strategy(
        ctx,
        reserve={"mode": "fixed", "fixed_usd": 2000},
        universe=[{"symbol": "VMFXX", "sec_type": "MUTUALFUND", "source": "fundamental"}],
    )
    intents = strategy.plan(ctx, ACCOUNT)

    assert intents[0].cash_quantity == Decimal("6000")
    assert intents[0].quantity is None


def test_below_minimum_plans_nothing(ctx, broker: SimulatedBroker):
    broker.set_cash(ACCOUNT, Decimal("5050")).set_value(ACCOUNT, "NetLiquidation", Decimal("5050"))
    broker.set_yield("SGOV", Decimal("5.0")).set_price("SGOV", Decimal("100"))

    assert _strategy(ctx).plan(ctx, ACCOUNT) == []


def test_unknown_yields_plan_nothing(ctx, broker: SimulatedBroker):
    broker.set_cash(ACCOUNT, Decimal("10000"))
    broker.set_yield("SGOV", None).set_yield("BIL", None)

    assert _strategy(ctx).plan(ctx, ACCOUNT) == []


def test_per_account_reserve_override(ctx, broker: SimulatedBroker):
    broker.set_cash(ACCOUNT, Decimal("10000")).set_value(
        ACCOUNT, "NetLiquidation", Decimal("100000")
    )
    broker.set_yield("SGOV", Decimal("5.0")).set_price("SGOV", Decimal("100"))

    strategy = _strategy(ctx, accounts={ACCOUNT: {"enabled": True, "reserve_usd": 9000}})
    intents = strategy.plan(ctx, ACCOUNT)

    assert intents[0].quantity == Decimal("10")  # (10000 - 9000) / 100


def test_negative_and_zero_cash(ctx, broker: SimulatedBroker):
    broker.set_cash(ACCOUNT, Decimal("-500"))
    broker.set_yield("SGOV", Decimal("5.0")).set_price("SGOV", Decimal("100"))

    assert _strategy(ctx).plan(ctx, ACCOUNT) == []


def test_enabled_accounts_respects_overrides(ctx, broker: SimulatedBroker):
    broker._accounts = ["DU1", "DU2"]  # noqa: SLF001
    ctx.accounts = ["DU1", "DU2"]
    strategy = _strategy(ctx, accounts={"DU2": {"enabled": False}})
    assert strategy.enabled_accounts(ctx) == ["DU1"]


def test_universe_filtered_by_base_currency(ctx, broker: SimulatedBroker):
    broker.set_base_currency(ACCOUNT, "CAD")
    broker.set_balance(ACCOUNT, "CAD", Decimal("100000")).set_value(
        ACCOUNT, "NetLiquidation", Decimal("100000")
    )
    broker.set_yield("SGOV", Decimal("9.0")).set_price("SGOV", Decimal("100"))
    broker.set_yield("CBIL", Decimal("3.0")).set_price("CBIL", Decimal("50"))

    strategy = _strategy(
        ctx,
        universe=[
            {"symbol": "SGOV", "sec_type": "STK", "currency": "USD"},
            {"symbol": "CBIL", "sec_type": "STK", "exchange": "TSE", "currency": "CAD"},
        ],
    )
    intents = strategy.plan(ctx, ACCOUNT)
    # SGOV has the higher yield but is USD -> ignored for a CAD account.
    assert intents[0].instrument.symbol == "CBIL"


def test_fallback_yield_used_when_feed_unavailable(ctx, broker: SimulatedBroker):
    broker.set_base_currency(ACCOUNT, "CAD")
    broker.set_balance(ACCOUNT, "CAD", Decimal("100000")).set_value(
        ACCOUNT, "NetLiquidation", Decimal("100000")
    )
    broker.set_yield("CBIL", None)  # feed unavailable
    broker.set_price("CBIL", Decimal("50"))

    strategy = _strategy(
        ctx,
        universe=[
            {
                "symbol": "CBIL",
                "sec_type": "STK",
                "exchange": "TSE",
                "currency": "CAD",
                "fallback_yield": 3.3,
            }
        ],
    )
    intents = strategy.plan(ctx, ACCOUNT)
    assert intents[0].instrument.symbol == "CBIL"
