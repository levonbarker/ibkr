from __future__ import annotations

from decimal import Decimal

from ibkr_trader.broker.simulated import SimulatedBroker
from ibkr_trader.core.config import AppConfig
from ibkr_trader.core.engine import Engine
from ibkr_trader.state.store import Store

ACCOUNT = "DU1111111"


def _config(dry_run: bool, *, kill_switch: bool = False) -> AppConfig:
    return AppConfig.model_validate(
        {
            "runtime": {
                "dry_run": dry_run,
                "accounts": {ACCOUNT: {"enabled": True}},
                "guards": {"kill_switch": kill_switch},
            },
            "strategies": {
                "cash_sweep": {
                    "enabled": True,
                    "reserve": {"mode": "fixed", "fixed_usd": 5000},
                    "min_order_usd": 100,
                    "universe": [{"symbol": "SGOV", "sec_type": "STK"}],
                }
            },
        }
    )


def _broker() -> SimulatedBroker:
    b = SimulatedBroker()
    b.set_cash(ACCOUNT, Decimal("10000")).set_value(ACCOUNT, "NetLiquidation", Decimal("100000"))
    b.set_yield("SGOV", Decimal("5.0")).set_price("SGOV", Decimal("100"))
    return b


def test_dry_run_plans_but_does_not_transmit(tmp_path):
    store = Store(tmp_path / "a.sqlite3")
    broker = _broker()
    results = Engine(_config(dry_run=True), broker, store).run()

    assert [r.status for r in results] == ["DRY_RUN"]
    assert broker.placed == []
    store.close()


def test_live_run_transmits(tmp_path):
    store = Store(tmp_path / "b.sqlite3")
    broker = _broker()
    results = Engine(_config(dry_run=False), broker, store).run()

    assert [r.status for r in results] == ["SUBMITTED"]
    assert len(broker.placed) == 1
    store.close()


def test_second_run_same_day_is_idempotent(tmp_path):
    store = Store(tmp_path / "c.sqlite3")
    broker = _broker()
    config = _config(dry_run=False)

    first = Engine(config, broker, store).run()
    second = Engine(config, broker, store).run()

    assert first[0].status == "SUBMITTED"
    assert second[0].status == "SKIPPED"
    assert second[0].message == "duplicate order_ref"
    assert len(broker.placed) == 1
    store.close()


def test_dry_run_does_not_block_later_live_run(tmp_path):
    store = Store(tmp_path / "f.sqlite3")
    broker = _broker()

    dry = Engine(_config(dry_run=True), broker, store).run()
    live = Engine(_config(dry_run=False), broker, store).run()

    assert dry[0].status == "DRY_RUN"
    assert live[0].status == "SUBMITTED"
    assert len(broker.placed) == 1
    store.close()


def test_kill_switch_skips(tmp_path):
    store = Store(tmp_path / "d.sqlite3")
    broker = _broker()
    results = Engine(_config(dry_run=False, kill_switch=True), broker, store).run()

    assert [r.status for r in results] == ["SKIPPED"]
    assert broker.placed == []
    store.close()


def test_allowlist_guard_blocks_other_symbols(tmp_path):
    store = Store(tmp_path / "e.sqlite3")
    broker = _broker()
    config = _config(dry_run=False)
    config.runtime.guards.allowed_symbols = ["BIL"]
    results = Engine(config, broker, store).run()

    assert results[0].status == "SKIPPED"
    assert "not in allowlist" in results[0].message
    store.close()
