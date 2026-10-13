#!/usr/bin/env bash
# Bootstrap para pasar de un deploy.sh antiguo a la versión validada del commit destino.
# Ejecutar SOLO después del preflight remoto y las verificaciones del workflow.
set -Eeuo pipefail
DEPLOY_DIR="$(pwd -P)"
cd "$DEPLOY_DIR"
: "${EXPECTED_COMMIT:?Commit obligatorio}"
case "$EXPECTED_COMMIT" in
  *[!0-9a-fA-F]*|"") echo "SHA inválido"; exit 1 ;;
esac
test -s deploy/.env.production || { echo "Configuración ausente"; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Cambios versionados presentes, cancelar bootstrap" >&2
  exit 1
fi
git fetch --quiet origin main
if [ "$(git rev-parse origin/main)" != "$EXPECTED_COMMIT" ]; then
  echo "El destino main cambió, no actualizar" >&2
  exit 1
fi
if ! git merge-base --is-ancestor HEAD "$EXPECTED_COMMIT"; then
  echo "Historial divergente, no actualizar" >&2
  exit 1
fi
# Protección adicional sin borrar ni ocultar archivos locales.
if ! git -c advice.detachedHead=false read-tree -n -m HEAD "$EXPECTED_COMMIT" 2>/dev/null; then
  echo "Colisión potencial con archivos locales; abortar" >&2
  exit 1
fi
compose=(docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml)
if ! "${compose[@]}" ps --status running db | grep -q db; then
  echo "PostgreSQL no está funcionando; abortar" >&2
  exit 1
fi
mkdir -p deploy/backups
backup="deploy/backups/fact_central_bootstrap_$(date -u +%Y%m%dT%H%M%SZ).dump"
"${compose[@]}" exec -T db sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$backup"
if [ ! -s "$backup" ]; then
  echo "Respaldo bootstrap vacío; abortar" >&2
  exit 1
fi
if ! "${compose[@]}" exec -T db pg_restore --list < "$backup" >/dev/null; then
  echo "Archivo de respaldo PostgreSQL inválido; cancelar despliegue" >&2
  exit 1
fi
echo "Respaldo bootstrap completado."
git checkout main
git merge --ff-only "$EXPECTED_COMMIT"
test "$(git rev-parse HEAD)" = "$EXPECTED_COMMIT"
EXPECTED_COMMIT="$EXPECTED_COMMIT" bash deploy/deploy.sh
