#!/usr/bin/env bash
# Auditoría y copia verificable no destructivas.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV="${ENV_FILE:-$ROOT/deploy/.env.production}"
COMPOSE="$ROOT/deploy/docker-compose.production.yml"
OUT="${BACKUP_DIR:-$ROOT/deploy/backups/pre_reset}"
test -f "$ENV" || { echo "No existe env privado: $ENV" >&2; exit 1; }
command -v docker >/dev/null
command -v pg_restore >/dev/null || { echo "Se requiere pg_restore local para verificar archivo" >&2; exit 1; }
mkdir -p "$OUT"
chmod 700 "$OUT"
cd "$ROOT"
compose=(docker compose --env-file "$ENV" -f "$COMPOSE")
echo "== Servicios Docker / sin secretos =="
"${compose[@]}" ps
echo "== Base y usuario efectivos (desde contenedor) =="
"${compose[@]}" exec -T db sh -c 'printf "DATABASE=%s\nUSER=%s\n" "$POSTGRES_DB" "$POSTGRES_USER"'
echo "== Recuento de tablas =="
"${compose[@]}" exec -T db sh -c 'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from information_schema.tables where table_schema = '\''public'\''"'
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP="$OUT/.factcentral_$STAMP.dump.partial"
DUMP="$OUT/factcentral_$STAMP.dump"
trap 'rm -f "$TMP"' EXIT
"${compose[@]}" exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' > "$TMP"
test -s "$TMP"
pg_restore --list "$TMP" >/dev/null
mv "$TMP" "$DUMP"
chmod 600 "$DUMP"
sha256sum "$DUMP" > "$DUMP.sha256"
chmod 600 "$DUMP.sha256"
(cd "$OUT" && sha256sum -c "$(basename "$DUMP").sha256")
echo "BACKUP_VERIFICADO=$DUMP"
echo "ATENCION: pg_restore --list verifica integridad de catalogo, NO prueba restauracion completa."
echo "No se ha eliminado ni modificado ningun dato."
