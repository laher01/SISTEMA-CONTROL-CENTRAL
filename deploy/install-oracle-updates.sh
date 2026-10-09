#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ "$(id -un)" != "ubuntu" ]; then
  echo "Ejecutar con usuario ubuntu, no como root" >&2
  exit 1
fi
test -f deploy/.env.production || { echo "Falta archivo de configuración"; exit 1; }
test "$(stat -c %a deploy/.env.production)" = "600" || { echo "El archivo .env.production debe tener permisos 600"; exit 1; }
docker info >/dev/null || { echo "Docker sin permisos; comprobar grupo docker"; exit 1; }
docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml config --quiet
git diff --quiet && git diff --cached --quiet || { echo "Hay modificaciones locales; no activar todavía"; exit 1; }

sudo install -m 0644 deploy/systemd/factcentral-update.service /etc/systemd/system/factcentral-update.service
sudo install -m 0644 deploy/systemd/factcentral-update.timer /etc/systemd/system/factcentral-update.timer
sudo systemctl daemon-reload
sudo systemctl enable --now factcentral-update.timer
echo "===== TEMPORIZADOR ====="
systemctl --no-pager status factcentral-update.timer
echo "===== PROXIMA EJECUCION ====="
systemctl list-timers factcentral-update.timer --no-pager
