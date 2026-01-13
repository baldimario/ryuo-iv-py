#!/usr/bin/env bash
# Uninstall script for ryuoctl: stop service, remove files and user
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root (or with sudo)"
  exit 1
fi

APP_ROOT=/opt/ryuoctl
BIN=/usr/local/bin/ryuoctl
SERVICE=/etc/systemd/system/ryuoctld.service
USER=ryuoctl

echo "Stopping and disabling systemd service if present"
if systemctl list-units --full -all | grep -Fq ryuoctld.service; then
  systemctl stop ryuoctld.service || true
  systemctl disable ryuoctld.service || true
fi

echo "Removing systemd unit"
rm -f ${SERVICE}
systemctl daemon-reload

echo "Removing udev rule if present"
UDEV_FILE=/etc/udev/rules.d/99-ryuo.rules
if [ -f "${UDEV_FILE}" ]; then
  rm -f "${UDEV_FILE}"
  udevadm control --reload-rules || true
  udevadm trigger || true
fi

echo "Removing wrapper and app"
rm -f ${BIN}
rm -rf ${APP_ROOT}

echo "Optionally removing user ${USER} (not forced)."
if id -u ${USER} >/dev/null 2>&1; then
  userdel ${USER} || true
fi

echo "Uninstall complete."
