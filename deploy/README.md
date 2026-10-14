# Deployment

Operational scaffolding to run **IB Gateway under IBC** so `ibkr-run` always has
a logged-in Gateway to connect to, plus optional systemd units for the daily
sweep.

```
deploy/
  install.sh                     # installs units + config templates (needs sudo)
  uninstall.sh
  gateway/
    config.ini.example           # -> /etc/ibkr/config.ini   (credentials, mode 600)
    gateway.env.example          # -> /etc/ibkr/gateway.env  (paths/version/display)
    run-gateway.sh               # -> /opt/ibkr/run-gateway.sh
  systemd/
    ib-gateway.service           # keeps Gateway+IBC alive (Restart=always)
    ibkr-sweep.service           # oneshot: `uv run ibkr-run`
    ibkr-sweep.timer             # weekdays 15:30 (optional)
```

## Prerequisites

- **Offline IB Gateway** installed to `~/Jts/<version>/`. The offline build is
  required (IBC does not work with the self-updating TWS/Gateway). It bundles
  its own JRE, so no system Java is needed.
- **IBC** extracted to `/opt/ibc` (IBC is retired as of Sep 2026; use the final
  release). Make the scripts executable:
  `sudo chmod +x /opt/ibc/*.sh /opt/ibc/scripts/*.sh`
- A display. WSLg provides `DISPLAY=:0` (already true in this environment); for
  headless use `xvfb-run` or a persistent `Xvfb :99`.

## Install

```bash
sudo deploy/install.sh
```

Then edit the two generated files:

- `/etc/ibkr/config.ini` — `IbLoginId`, `IbPassword`, `TradingMode`.
- `/etc/ibkr/gateway.env` — `TWS_MAJOR_VRSN` (from `Help > About IB Gateway`,
  e.g. `1045`), paths, `DISPLAY`.

Start and watch:

```bash
sudo systemctl start ib-gateway
journalctl -u ib-gateway -f          # systemd view
less /var/log/ibkr/ibc/*.txt         # IBC diagnostic log
```

Once logged in:

```bash
uv run ibkr-run --dry-run            # plan only, no orders
```

## Daily sweep (optional)

Scheduling was intentionally deferred, but the units are provided:

```bash
sudo systemctl enable --now ibkr-sweep.timer
systemctl list-timers ibkr-sweep.timer
```

`ibkr-sweep.service` loads the repo's `.env`, so `IBKR_*` overrides apply.
Run `ibkr-sweep.service` manually with `sudo systemctl start ibkr-sweep`.

## Notes

- `AcceptIncomingConnectionAction=reject` is set; whitelist `127.0.0.1` in the
  Gateway's API settings and enable the API socket on port `4002` (paper) /
  `4001` (live) to match `config/config.yaml`.
- Auto-restart uses `AutoRestartTime`; a weekly full re-auth
  (`ColdRestartTime`) is required by IBKR. You handle the 2FA prompts.
- The service runs as `$SUDO_USER` by default; override with
  `SERVICE_USER=<name> sudo -E deploy/install.sh`.
