#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${1:-}"
if [[ -z "${REPO_URL}" ]]; then
  echo "Usage: $0 <git-repo-url>"
  exit 2
fi

echo "[1/8] Installing system packages"
apt-get update
apt-get install -y git python3 python3-venv python3-pip ca-certificates

echo "[2/8] Creating system user issbot"
if ! id -u issbot >/dev/null 2>&1; then
  useradd --system --home /opt/iss-horizon --shell /usr/sbin/nologin issbot
fi

echo "[3/8] Cloning repository"
if [[ -d /opt/iss-horizon/.git ]]; then
  git -C /opt/iss-horizon pull --ff-only
else
  rm -rf /opt/iss-horizon
  git clone "${REPO_URL}" /opt/iss-horizon
fi

chown -R issbot:issbot /opt/iss-horizon

echo "[4/8] Creating Python virtual environment"
sudo -u issbot python3 -m venv /opt/iss-horizon/.venv
sudo -u issbot /opt/iss-horizon/.venv/bin/pip install --upgrade pip
sudo -u issbot /opt/iss-horizon/.venv/bin/pip install -e /opt/iss-horizon

echo "[5/8] Installing environment template"
install -d -m 0750 /etc/iss-horizon
if [[ ! -f /etc/iss-horizon/iss-horizon.env ]]; then
  cp /opt/iss-horizon/.env.example /etc/iss-horizon/iss-horizon.env
  chmod 0640 /etc/iss-horizon/iss-horizon.env
fi

echo "[6/8] Installing systemd units"
cp /opt/iss-horizon/systemd/iss-horizon.service /etc/systemd/system/iss-horizon.service
cp /opt/iss-horizon/systemd/iss-horizon.timer /etc/systemd/system/iss-horizon.timer
systemctl daemon-reload

echo "[7/8] Enabling timer"
systemctl enable --now iss-horizon.timer

echo "[8/8] Done"
echo "WARNING: Edit /etc/iss-horizon/iss-horizon.env and set SMTP_* and REPORT_TO before relying on delivery."
echo "Check status with: systemctl status iss-horizon.timer"
