#!/usr/bin/env bash
#
# Remove the systemd units installed by install.sh.
# Leaves /etc/ibkr (credentials) in place unless --purge is given.
#
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Please run as root (sudo)." >&2
    exit 1
fi

systemctl disable --now ibkr-sweep.timer 2>/dev/null || true
systemctl disable --now ib-gateway.service 2>/dev/null || true

for unit in ib-gateway.service ibkr-sweep.service ibkr-sweep.timer; do
    rm -f "/etc/systemd/system/${unit}"
    echo "removed /etc/systemd/system/${unit}"
done

rm -f /opt/ibkr/run-gateway.sh
rmdir /opt/ibkr 2>/dev/null || true

systemctl daemon-reload

if [[ "${1:-}" == "--purge" ]]; then
    rm -rf /etc/ibkr
    echo "purged /etc/ibkr"
else
    echo "left /etc/ibkr in place (use --purge to remove credentials too)"
fi
