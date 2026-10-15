#!/usr/bin/env bash
# Preflight aislado: crea backup fresco de PostgreSQL y prueba restauracion, sin tocar datos originales.
set -Eeuo pipefail
umask 077
cd "$(dirname "$0")/.."
test -s deploy/.env.production
compose=(docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml)
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dir="deploy/backups/audit"
mkdir -p "$dir"
chmod 700 "$dir"
dump="$dir/factcentral_predeploy_${stamp}.dump"
tmp="${dump}.partial"
db="factcentral_predeploy_${stamp}_$$"
created=0
cleanup() {
  if [ "$created" -eq 1 ]; then
    "${compose[@]}" exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$1"' sh "$db" </dev/null || true
  fi
  rm -f -- "$tmp"
}
trap cleanup EXIT
test -z "${EXPECTED_HOST:-}" || test "$EXPECTED_HOST" = "132.145.233.172"
"${compose[@]}" ps --status running db | grep -q db
# Advisory lock is not required: pg_dump provides a transactionally consistent snapshot.
"${compose[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$tmp"
test -s "$tmp"
"${compose[@]}" exec -T db pg_restore --list < "$tmp" >/dev/null
mv "$tmp" "$dump"
sha256sum "$dump" > "$dump.sha256"
sha256sum -c "$dump.sha256"
# Snapshot metadata is read from the restored copy, NOT from a concurrently changing live DB.
"${compose[@]}" exec -T db sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$db" </dev/null
created=1
"${compose[@]}" exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" --no-owner --no-acl --exit-on-error -d "$1"' sh "$db" < "$dump"
count="$("${compose[@]}" exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -Atc "select count(*) from documentos"' sh "$db" </dev/null)"
version="$("${compose[@]}" exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -Atc "select version_num from alembic_version"' sh "$db" </dev/null)"
test "$count" -ge 0
test -n "$version"
echo "BACKUP_RECIENTE: $dump"
echo "SHA256_VERIFICADO"
echo "RESTAURACION_TEMPORAL_OK"
echo "DOCUMENTOS_RESTAURADOS: $count"
echo "ALEMBIC_VERSION_RESPALDO: $version"
echo "BASE_PRODUCTIVA_NO_MODIFICADA"
echo "PENDIENTE: cotejo temporal con documentos en volumen, migracion 0037 y downgrade/reupgrade en DB aislada"
