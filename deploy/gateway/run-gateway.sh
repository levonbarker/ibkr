#!/usr/bin/env bash
#
# Launch IB Gateway under IBC, driven entirely by environment variables.
#
# This is what the ib-gateway systemd unit runs. It calls IBC's own
# ibcstart.sh service script (the same one gatewaystart.sh uses) so we avoid
# the xterm banner wrapper that needs an interactive terminal.
#
# Usage: run-gateway.sh
#   Reads config from $GATEWAY_ENV_FILE (default /etc/ibkr/gateway.env).
#
set -euo pipefail

ENV_FILE="${GATEWAY_ENV_FILE:-/etc/ibkr/gateway.env}"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

: "${TWS_MAJOR_VRSN:?set TWS_MAJOR_VRSN in $ENV_FILE}"
IBC_PATH="${IBC_PATH:-/opt/ibc}"
TWS_PATH="${TWS_PATH:-$HOME/Jts}"
TWS_SETTINGS_PATH="${TWS_SETTINGS_PATH:-$TWS_PATH}"
IBC_INI="${IBC_INI:-/etc/ibkr/config.ini}"
TRADING_MODE="${TRADING_MODE:-paper}"
TWOFA_TIMEOUT_ACTION="${TWOFA_TIMEOUT_ACTION:-exit}"
LOG_PATH="${LOG_PATH:-/var/log/ibkr/ibc}"
DISPLAY="${DISPLAY:-:0}"

[[ -f "${IBC_PATH}/scripts/ibcstart.sh" ]] || {
    echo "ERROR: ${IBC_PATH}/scripts/ibcstart.sh not found (install IBC to ${IBC_PATH})" >&2
    exit 1
}

mkdir -p "$LOG_PATH" "$TWS_SETTINGS_PATH"

IBC_VRSN="$(cat "${IBC_PATH}/version" 2>/dev/null || echo unknown)"
export TWS_MAJOR_VRSN IBC_PATH TWS_PATH TWS_SETTINGS_PATH IBC_INI
export TRADING_MODE TWOFA_TIMEOUT_ACTION LOG_PATH DISPLAY
export IBC_VRSN APP=GATEWAY

exec "${IBC_PATH}/scripts/ibcstart.sh" "${TWS_MAJOR_VRSN}" -g \
    "--tws-path=${TWS_PATH}" \
    "--tws-settings-path=${TWS_SETTINGS_PATH}" \
    "--ibc-path=${IBC_PATH}" \
    "--ibc-ini=${IBC_INI}" \
    "--mode=${TRADING_MODE}" \
    "--on2fatimeout=${TWOFA_TIMEOUT_ACTION}"
