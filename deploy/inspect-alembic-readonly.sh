#!/usr/bin/env bash
# Diagnóstico Alembic en VPS antigua: exclusivamente lectura; no migrar ni restaurar.
set -Eeuo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
test -s deploy/.env.production || { echo "::error::Configuración de producción ausente"; exit 1; }
compose=(docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml)
echo "Commit instalado: $(git rev-parse HEAD)"
echo "Versiones Alembic registradas en PostgreSQL (solo lectura):"
"${compose[@]}" exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version ORDER BY version_num"' </dev/null
echo "Herramientas disponibles:"
command -v pg_restore >/dev/null || { echo "::error::Falta pg_restore"; exit 1; }
echo "Diagnóstico Alembic completado: no se ejecutaron migraciones."
