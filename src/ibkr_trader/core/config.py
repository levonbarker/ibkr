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


def load_config(path: str | Path = "config/config.yaml") -> AppConfig:
    data: dict[str, Any] = {}
    p = Path(path)
    if p.exists():
        data = yaml.safe_load(p.read_text()) or {}

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
