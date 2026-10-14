"""Run reporting / notifications.

Currently logs a structured summary. Kept behind a small interface so an
email/Telegram/Slack backend can be dropped in later without touching callers.
"""

from __future__ import annotations

from collections import Counter

from ibkr_trader.core.intent import Result
from ibkr_trader.util.logging import get_logger

log = get_logger("notify")


class Notifier:
    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose

    def run_started(self, accounts: list[str], dry_run: bool) -> None:
        mode = "DRY-RUN" if dry_run else "LIVE"
        log.info("run started [%s] accounts=%s", mode, ", ".join(accounts) or "none")

    def run_finished(self, results: list[Result]) -> None:
        counts = Counter(r.status for r in results)
        log.info("run finished: %d intents %s", len(results), dict(counts))
        if not self.verbose:
            return
        for r in results:
            i = r.intent
            size = (
                f"${i.cash_quantity}"
                if i.cash_quantity is not None
                else f"{i.quantity} {i.instrument.symbol}"
            )
            log.info(
                "  [%s] %s %s %s (%s) %s",
                r.status,
                i.side,
                size,
                f"acct={i.account}",
                i.strategy,
                r.message,
            )
