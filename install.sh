#!/usr/bin/env bash
# Install script for ryuoctl: copies app to /opt, creates venv, wrapper and systemd unit
set -euo pipefail

PORT=55667
while getopts ":p:" opt; do
  case ${opt} in
    p ) PORT=$OPTARG ;;
    \? ) echo "Usage: $0 [-p PORT]"; exit 1 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root (or with sudo)"
  exit 1
fi

APP_DIR=/opt/ryuoctl/app
VENV_DIR=/opt/ryuoctl/venv
BIN=/usr/local/bin/ryuoctl
SERVICE=/etc/systemd/system/ryuoctld.service
echo "Installing ryuoctl to ${APP_DIR} (port ${PORT})"

mkdir -p /opt/ryuoctl
rsync -a --exclude .git --exclude __pycache__ ./ ${APP_DIR}/

# Run service as root; ensure app owned by root
chown -R root:root /opt/ryuoctl

echo "Creating virtualenv at ${VENV_DIR}"
python3 -m venv ${VENV_DIR}
${VENV_DIR}/bin/pip install --upgrade pip
if [[ -f "${APP_DIR}/requirements.txt" ]]; then
  ${VENV_DIR}/bin/pip install -r ${APP_DIR}/requirements.txt
fi

echo "Creating wrapper ${BIN}"
cat > ${BIN} <<EOF
#!/bin/sh
exec ${VENV_DIR}/bin/python ${APP_DIR}/src/main.py "\$@"
EOF
chmod +x ${BIN}


echo "Installing systemd unit"
sed "s|__PORT__|${PORT}|g" ${APP_DIR}/packaging/ryuoctld.service > ${SERVICE}
chown root:root ${SERVICE}
chmod 644 ${SERVICE}

echo "Installing udev rule for Ryuo device (owned by root)"
UDEV_FILE=/etc/udev/rules.d/99-ryuo.rules
cat > ${UDEV_FILE} <<UDEVRULE
# Set permissions on hidraw device produced for Ryuo USB device
ACTION=="add", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1c75", ATTRS{idProduct}=="1c76", MODE="0660", GROUP="root"

# Fallback: also set permissions on usb add events (some systems)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="1c75", ATTR{idProduct}=="1c76", MODE="0660", GROUP="root"
UDEVRULE
chmod 644 ${UDEV_FILE}

echo "Reloading udev rules"
udevadm control --reload-rules
udevadm trigger || true

echo "udev rule installed; hidraw device will be owned by group 'root' when device is plugged"

systemctl daemon-reload

echo "Enabling and starting ryuoctld.service now"
if systemctl enable --now ryuoctld.service; then
  echo "Service enabled and started"
else
  echo "Failed to enable/start service automatically; you can enable it manually with: sudo systemctl enable --now ryuoctld.service"
fi

echo "Installation complete. The systemd unit has been created at ${SERVICE}."
