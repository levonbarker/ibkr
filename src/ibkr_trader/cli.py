"""Command-line entry point: run enabled strategies once."""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from ibkr_trader.broker.ibkr import IbkrBroker
from ibkr_trader.broker.simulated import demo_broker
from ibkr_trader.core.config import load_config
from ibkr_trader.core.engine import Engine
from ibkr_trader.state.store import Store
from ibkr_trader.util.logging import setup_logging
from ibkr_trader.util.notify import Notifier


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ibkr-run", description="Run IBKR strategies once")
    p.add_argument("--config", default=None, help="path to config yaml (default: auto-locate)")
    p.add_argument("--live", action="store_true", help="transmit real orders (disables dry-run)")
    p.add_argument("--dry-run", action="store_true", help="force planning only, never transmit")
    p.add_argument(
        "--simulate",
        action="store_true",
        help="run against an in-memory broker (no Gateway required)",
    )
    p.add_argument(
        "--strategy",
        action="append",
        dest="strategies",
        default=None,
        help="only run this strategy (repeatable)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.live:
        config.runtime.dry_run = False
    if args.dry_run:
        config.runtime.dry_run = True
    if args.strategies:
        wanted = set(args.strategies)
        config.strategies = {
            name: block for name, block in config.strategies.items() if name in wanted
        }

    setup_logging(config.runtime.log_level)

    store = Store(config.runtime.db_path)
    broker = demo_broker() if args.simulate else IbkrBroker(config.gateway)
    if args.simulate:
        config.runtime.accounts = {}
    try:
        broker.connect()
        results = Engine(config, broker, store, Notifier()).run()
    finally:
        broker.disconnect()
        store.close()

    counts = Counter(r.status for r in results)
    print(f"done: {dict(counts)}")
    return 1 if counts.get("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main())
