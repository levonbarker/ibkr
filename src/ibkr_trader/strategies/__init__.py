"""Strategy plugins.

Importing this package registers every bundled strategy with the registry.
Add new strategies by importing them here.
"""

from ibkr_trader.strategies import cash_sweep, noop  # noqa: F401

__all__ = ["cash_sweep", "noop"]
