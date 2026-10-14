"""Strategy registry.

Strategies self-register via the :func:`register` decorator. Adding a new
strategy is a matter of dropping a package under ``ibkr_trader.strategies`` and
decorating its class -- nothing in ``core`` needs to change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ibkr_trader.strategies.base import Strategy

_REGISTRY: dict[str, type[Strategy]] = {}


def register(cls: type[Strategy]) -> type[Strategy]:
    if not cls.name:
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    if cls.name in _REGISTRY:
        raise ValueError(f"duplicate strategy name: {cls.name!r}")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> type[Strategy]:
    _ensure_loaded()
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown strategy {name!r}; registered: {sorted(_REGISTRY)}") from None


def available() -> list[str]:
    _ensure_loaded()
    return sorted(_REGISTRY)


_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    import ibkr_trader.strategies  # noqa: F401  (triggers submodule imports)
