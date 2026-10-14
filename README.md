# ibkr

Multi-account, multi-strategy trading engine for Interactive Brokers.

Design goal: **strategies are pure plugins**. The core knows how to connect,
feed account context, enforce safety, transmit orders, and keep a ledger. Each
trading idea is a self-contained strategy package. The first one is a daily
**cash sweep**; more will follow.

## How it works

```
connect ──► build Context (accounts, cash, positions, yields)
        ──► for each enabled strategy, per account:
                strategy.plan(ctx, account) -> [Intent]   # pure, no IO
        ──► guards (kill switch, allowlist, min/max notional)
        ──► dry-run? record : transmit
        ──► persist results to SQLite (idempotency + audit)
```

A strategy never touches the broker, the clock, or the network. It returns
`Intent` objects describing what it *wants* to do; the engine decides whether
and how that happens. This is what makes strategies trivially testable.

## Quickstart (no Gateway required)

```bash
uv sync
uv run ibkr-run --simulate          # dry-run against an in-memory broker
uv run ibkr-run --simulate --live   # "transmit" against the in-memory broker
uv run pytest                       # unit + integration tests
uv run ruff check . && uv run mypy
```

Against a real IB Gateway / TWS:

```bash
cp .env.example .env                # set IBKR_HOST / IBKR_PORT / IBKR_ACCOUNTS
uv run ibkr-run --dry-run           # plan only (default)
uv run ibkr-run --live              # transmit real orders
uv run ibkr-run --strategy cash_sweep
```

`--live` is required to transmit; the config default is `dry_run: true`.
Environment variables (`IBKR_DRY_RUN`, `IBKR_KILL_SWITCH`, `IBKR_ACCOUNTS`)
override the YAML.

## Repository layout

```
config/config.yaml           # gateway, runtime, and per-strategy config
src/ibkr_trader/
  cli.py                     # `ibkr-run` entry point
  core/                      # engine, context, intent, registry, config
  broker/                    # base protocol, ib_async impl, simulated impl, market data
  strategies/                # base + plugins (noop, cash_sweep)
  state/store.py             # SQLite ledger (idempotency, yield cache)
  util/                      # guards, market hours, logging, notify
tests/                       # 33 unit + simulated integration tests
```

## Configuration

See `config/config.yaml`. Per-strategy blocks live under `strategies:`; each
strategy validates its own block with a pydantic model.

```yaml
strategies:
  cash_sweep:
    enabled: true
    reserve: {mode: max, fixed_usd: 5000, percent: 1.0}
    min_order_usd: 100
    max_order_usd: 250000
    universe:
      - {symbol: SGOV, sec_type: STK, exchange: SMART, source: ib_dividends}
      - {symbol: BIL,  sec_type: STK, exchange: SMART, source: ib_dividends}
```

### Cash sweep logic

1. `sweepable = min(cash, settled) - reserve` (reserve = fixed / percent / max).
2. Rank the universe by current yield (memoised + cached in SQLite).
3. Size: mutual funds use dollar-based `cashQty`; ETFs use whole shares.
4. Emit one `Intent` per account; the engine handles guards and idempotency.

Yield sources: `ib_dividends` (IB Dividends tick 456) for ETFs,
`fundamental` (`ReportsFinSummary`) for money market funds. Unknown yields are
never guessed -- the account is skipped and logged.

## Adding a strategy

```python
from ibkr_trader.core.registry import register
from ibkr_trader.strategies.base import Strategy, StrategyConfig

@register
class MyStrategy(Strategy):
    name = "my_strategy"
    config_cls = StrategyConfig

    def enabled_accounts(self, ctx): return ctx.accounts
    def plan(self, ctx, account):
        return []   # build Intent(...) objects here
```

Drop the module under `src/ibkr_trader/strategies/`, import it in
`strategies/__init__.py`, add a block to `config/config.yaml`. Nothing in
`core/` changes.

## Safety

- `dry_run` defaults to true; `--live` is explicit.
- Kill switch (`IBKR_KILL_SWITCH=1` or config).
- Per-symbol allowlist, min/max notional guards.
- Idempotency: a given `(strategy, date, account, instrument)` submits at most
  once; re-runs are skipped, dry-runs do not block a later live run.
- Every intent is recorded in the SQLite ledger for audit.

## Gateway / IBC (operational notes)

The `deploy/` folder contains ready-to-install scaffolding: an IBC
`config.ini` template, a `gateway.env`, a `run-gateway.sh` launcher, and
systemd units (a persistent `ib-gateway.service` plus an optional daily
`ibkr-sweep.timer`). See [`deploy/README.md`](deploy/README.md) for the steps.

- Run **IB Gateway** (offline Linux build, bundles its own JRE) with API enabled,
  port `4002` (paper) / `4001` (live), trusted IP `127.0.0.1`.
- Use **IBC** for auto-login / daily restart. IBC is retired (Sep 2026) but the
  final release still works; pin it. You handle the 2FA prompts.
- Native Gateway is a GUI app -- WSLg (`DISPLAY=:0`) or `Xvfb` provides the
  display.
- Scheduling is optional and off by default; runs are manual unless you enable
  `ibkr-sweep.timer`.
