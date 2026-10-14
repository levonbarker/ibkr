from __future__ import annotations

from decimal import Decimal

from ibkr_trader.core.intent import Instrument, Intent, Result
from ibkr_trader.state.store import Store


def _intent(ref: str = "r1") -> Intent:
    return Intent(
        account="DU1",
        instrument=Instrument("SGOV"),
        side="BUY",
        strategy="cash_sweep",
        cash_quantity=Decimal("1000"),
        order_ref=ref,
    )


def test_record_and_seen(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    run = store.start_run(["DU1"], dry_run=False)
    intent = _intent()
    store.record(run, intent, Result(intent, "SUBMITTED", "ok", order_id=1))

    assert store.seen_order_ref("r1") is True
    assert store.seen_order_ref("other") is False
    store.close()


def test_skipped_does_not_block_idempotency(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    run = store.start_run(["DU1"], dry_run=False)
    intent = _intent("r2")
    store.record(run, intent, Result(intent, "SKIPPED", "kill switch"))

    assert store.seen_order_ref("r2") is False
    store.close()


def test_yield_cache_roundtrip(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    store.put_yield("ib_dividends:SGOV.STK@SMART", Decimal("5.12"), "ib_dividends")
    rec = store.get_yield("ib_dividends:SGOV.STK@SMART")

    assert rec is not None
    assert rec.value == Decimal("5.12")
    assert rec.source == "ib_dividends"
    store.close()
