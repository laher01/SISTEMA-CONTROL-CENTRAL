#!/usr/bin/env bash
# Auditoría de solo lectura de FACT CENTRAL en VPS antigua.
# No actualiza repositorio, no migra BD y no cambia servicios.
set -Eeuo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
echo "AUDITORIA_COMIENZO"
echo "SHA_VPS=$(git rev-parse HEAD)"
echo "RAMA_VPS=$(git branch --show-current)"
if [ -z "$(git status --porcelain --untracked-files=no)" ]; then
  echo "TRACKED_TREE_LIMPIO=SI"
else
  echo "TRACKED_TREE_LIMPIO=NO"
fi

if [ ! -f deploy/.env.production ]; then
  echo "ENV_PRODUCCION=NO_ENCONTRADO"
  exit 2
fi

compose=(docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml)
echo "ESTADO_CONTENEDORES"
"${compose[@]}" ps --status running

echo "BACKEND_HTTP_HEALTH"
curl --fail --silent --show-error --max-time 8 \
  http://127.0.0.1:18080/health
printf '\n'

# `current` consulta la tabla alembic_version, NO aplica migraciones.
echo "ALEMBIC_VERSION_INSTALADA"
"${compose[@]}" exec -T backend uv run alembic current

echo "AUDITORIA_COMPLETADA_SOLO_LECTURA"
