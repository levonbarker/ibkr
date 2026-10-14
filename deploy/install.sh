#!/usr/bin/env bash
#
# Install the IB Gateway + sweep systemd units and config templates.
#
# Does NOT download IB Gateway or IBC (both require manual, licensed downloads).
# It sets up everything around them. Run with sudo.
#
# Usage:
#   sudo deploy/install.sh
#   SERVICE_USER=trader sudo -E deploy/install.sh
#
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Please run as root (sudo)." >&2
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
SERVICE_GROUP="${SERVICE_GROUP:-$(id -gn "${SERVICE_USER}")}"
SERVICE_HOME="$(getent passwd "${SERVICE_USER}" | cut -d: -f6)"

CONF_DIR=/etc/ibkr
LOG_DIR=/var/log/ibkr/ibc
LAUNCH_DIR=/opt/ibkr

echo "repo        : ${REPO_DIR}"
echo "service user: ${SERVICE_USER} (${SERVICE_GROUP}), home ${SERVICE_HOME}"

install -d -m 755 "${CONF_DIR}" "${LAUNCH_DIR}"
install -d -m 755 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" "${LOG_DIR}"

install -m 755 "${REPO_DIR}/deploy/gateway/run-gateway.sh" "${LAUNCH_DIR}/run-gateway.sh"

if [[ -f "${CONF_DIR}/config.ini" ]]; then
    echo "kept existing ${CONF_DIR}/config.ini"
else
    install -m 600 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" \
        "${REPO_DIR}/deploy/gateway/config.ini.example" "${CONF_DIR}/config.ini"
    echo "wrote ${CONF_DIR}/config.ini  <-- EDIT with your IBKR credentials"
fi

if [[ -f "${CONF_DIR}/gateway.env" ]]; then
    echo "kept existing ${CONF_DIR}/gateway.env"
else
    install -m 640 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" \
        "${REPO_DIR}/deploy/gateway/gateway.env.example" "${CONF_DIR}/gateway.env"
    sed -i \
        -e "s|^TWS_PATH=.*|TWS_PATH=${SERVICE_HOME}/Jts|" \
        -e "s|^TWS_SETTINGS_PATH=.*|TWS_SETTINGS_PATH=${SERVICE_HOME}/Jts|" \
        "${CONF_DIR}/gateway.env"
    echo "wrote ${CONF_DIR}/gateway.env  <-- set TWS_MAJOR_VRSN"
fi

render() {
    sed -e "s|@REPO_DIR@|${REPO_DIR}|g" \
        -e "s|@SERVICE_USER@|${SERVICE_USER}|g" "$1"
}

for unit in ib-gateway.service ibkr-sweep.service ibkr-sweep.timer; do
    render "${REPO_DIR}/deploy/systemd/${unit}" > "/etc/systemd/system/${unit}"
    echo "installed /etc/systemd/system/${unit}"
done

systemctl daemon-reload
systemctl enable ib-gateway.service

cat <<EOF

Done. Next steps:
  1. Install the OFFLINE IB Gateway (it bundles its own JRE) so it lives in
       ${SERVICE_HOME}/Jts/<TWS_MAJOR_VRSN>/
  2. Install IBC to /opt/ibc  (chmod +x /opt/ibc/*.sh /opt/ibc/scripts/*.sh)
  3. Edit ${CONF_DIR}/config.ini (credentials) and ${CONF_DIR}/gateway.env
       (TWS_MAJOR_VRSN, paths, DISPLAY)
  4. Start it:      sudo systemctl start ib-gateway
     Watch logs:    journalctl -u ib-gateway -f
     IBC logfile:   ${LOG_DIR}
  5. Verify API:    uv run ibkr-run --dry-run
  6. Optional daily sweep:
       sudo systemctl enable --now ibkr-sweep.timer
EOF
