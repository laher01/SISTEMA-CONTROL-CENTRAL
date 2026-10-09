#!/usr/bin/env bash
# Lightweight updater for a VPS that cannot accept inbound GitHub Actions SSH.
# Reuses the original deploy/deploy.sh, its backups, health checks and lock.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
git fetch --quiet origin main
local_sha="$(git rev-parse HEAD)"
remote_sha="$(git rev-parse origin/main)"
if [ "$local_sha" = "$remote_sha" ]; then
  echo "FACT CENTRAL: ya está en $local_sha"
  exit 0
fi
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "FACT CENTRAL: hay archivos locales sin registrar; revisión manual necesaria" >&2
  exit 1
fi
if ! git merge-base --is-ancestor "$local_sha" "$remote_sha"; then
  echo "FACT CENTRAL: main remoto no avanza linealmente. No se despliega" >&2
  exit 1
fi
# deploy.sh holds its own file lock, backs up PostgreSQL, builds and checks /health.
EXPECTED_COMMIT="$remote_sha" bash "$ROOT/deploy/deploy.sh"
