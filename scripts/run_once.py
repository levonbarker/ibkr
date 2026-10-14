#!/usr/bin/env python
"""Run all enabled strategies once (respects dry_run from config)."""

from ibkr_trader.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
