"""Application configuration: YAML plus environment overrides."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class GatewayConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 4002
    client_id: int = 10
    timeout: float = 30.0
    readonly: bool = False
    # 1 = realtime, 3 = delayed, 4 = delayed-frozen.
    market_data_type: int = 1


class AccountSetting(BaseModel):
    enabled: bool = True


class GuardSettings(BaseModel):
    kill_switch: bool = False
    max_order_usd: Decimal = Decimal("1000000")
    min_order_usd: Decimal = Decimal("1")
    allowed_symbols: list[str] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    dry_run: bool = True
    timezone: str = "America/New_York"
    log_level: str = "INFO"
    db_path: str = "state/ibkr.sqlite3"
    accounts: dict[str, AccountSetting] = Field(default_factory=dict)
    guards: GuardSettings = Field(default_factory=GuardSettings)


class AppConfig(BaseModel):
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    # strategy name -> raw config block (validated by each strategy's own model)
    strategies: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def enabled_strategies(self) -> dict[str, dict[str, Any]]:
        return {
            name: block for name, block in self.strategies.items() if block.get("enabled", True)
        }


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _repo_root() -> Path:
    # src/ibkr_trader/core/config.py -> repo root
    return Path(__file__).resolve().parents[3]


def resolve_config_path(path: str | Path | None) -> Path:
    """Locate the config file.

    An explicit path must exist. For the default (``None``), look in the
    current directory first, then the repo root, so runs work from anywhere.
    """
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"config file not found: {p}")
        return p
    for candidate in (
        Path.cwd() / "config" / "config.yaml",
        _repo_root() / "config" / "config.yaml",
    ):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("no config/config.yaml found; pass --config <path>")


def load_config(path: str | Path | None = None) -> AppConfig:
    resolved = resolve_config_path(path)
    data: dict[str, Any] = yaml.safe_load(resolved.read_text()) or {}

    config = AppConfig.model_validate(data)

    # Environment overrides (env wins over YAML, which wins over defaults).
    if host := os.getenv("IBKR_HOST"):
        config.gateway.host = host
    if port := os.getenv("IBKR_PORT"):
        config.gateway.port = int(port)
    if client_id := os.getenv("IBKR_CLIENT_ID"):
        config.gateway.client_id = int(client_id)
    if os.getenv("IBKR_DRY_RUN") is not None:
        config.runtime.dry_run = _env_bool("IBKR_DRY_RUN", config.runtime.dry_run)
    if os.getenv("IBKR_KILL_SWITCH") is not None:
        config.runtime.guards.kill_switch = _env_bool(
            "IBKR_KILL_SWITCH", config.runtime.guards.kill_switch
        )
    if accounts := os.getenv("IBKR_ACCOUNTS"):
        config.runtime.accounts = {
            a.strip(): AccountSetting(enabled=True) for a in accounts.split(",") if a.strip()
        }

    return config
