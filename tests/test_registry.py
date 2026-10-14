from __future__ import annotations

import pytest

from ibkr_trader.core import registry


def test_bundled_strategies_registered():
    names = registry.available()
    assert "noop" in names
    assert "cash_sweep" in names


def test_get_returns_class():
    cls = registry.get("cash_sweep")
    assert cls.name == "cash_sweep"


def test_unknown_strategy_raises():
    with pytest.raises(KeyError):
        registry.get("does_not_exist")
