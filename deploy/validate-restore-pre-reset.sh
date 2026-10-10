#!/usr/bin/env bash
# Verifica restauración completa en una base efímera del PostgreSQL de pruebas.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV="${ENV_FILE:-$ROOT/deploy/.env.production}"
COMPOSE="$ROOT/deploy/docker-compose.production.yml"
DUMP="${1:?Uso: validate-restore-pre-reset.sh ruta/dump}"
test -f "$ENV" && test -s "$DUMP"
DUMP="$(realpath "$DUMP")"
cd "$ROOT"
compose=(docker compose --env-file "$ENV" -f "$COMPOSE")
DB="fc_restore_check_$(date +%s)_$$"
clean() {
  "${compose[@]}" exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$1"' sh "$DB" >/dev/null 2>&1 || true
}
trap clean EXIT
echo "Creando base temporal aislada $DB"
"${compose[@]}" exec -T db sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$DB"
echo "Restaurando copia; no modifica base de FACT CENTRAL"
"${compose[@]}" exec -T db sh -c 'pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$1"' sh "$DB" < "$DUMP"
"${compose[@]}" exec -T db sh -c 'psql -X -U "$POSTGRES_USER" -d "$1" -Atc "select count(*) from information_schema.tables where table_schema = '\''public'\''"' sh "$DB"
echo "RESTAURACION_VERIFICADA en base temporal: $DB"
echo "La base temporal será eliminada al terminar."
