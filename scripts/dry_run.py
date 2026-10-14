#!/usr/bin/env python
"""Force a dry-run: plan orders but never transmit, regardless of config."""

from ibkr_trader.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["--dry-run"]))
