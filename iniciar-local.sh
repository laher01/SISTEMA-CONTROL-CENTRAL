#!/usr/bin/env bash
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$raiz/backend"
if [[ ! -f .env ]]; then
  cp .env.local.example .env
fi
uv sync
uv run python -m scripts.inicializar_local
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!

cd "$raiz/frontend"
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 &
frontend_pid=$!

detener() {
  kill "$frontend_pid" "$backend_pid" 2>/dev/null || true
}
trap detener EXIT INT TERM

echo "FACT CENTRAL disponible en http://127.0.0.1:5173"
echo "API y Swagger disponibles en http://127.0.0.1:8000/docs"
wait
