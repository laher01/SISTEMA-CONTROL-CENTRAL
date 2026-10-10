#!/usr/bin/env bash
# Solo respaldo y verificación no destructiva de FACT CENTRAL.
# No limpia tablas, no borra volúmenes, no despliega.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ENV_FILE="$ROOT/deploy/.env.production"
COMPOSE_FILE="$ROOT/deploy/docker-compose.production.yml"
test -f "$ENV_FILE" || { echo "Falta configuración de producción" >&2; exit 1; }
command -v docker >/dev/null
command -v sha256sum >/dev/null
command -v tar >/dev/null

exec 9>"$ROOT/deploy/.deploy.lock"
flock -n 9 || { echo "Hay otro proceso de despliegue/respaldo activo" >&2; exit 1; }
compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

# Debe existir base de datos operativa y el volumen de adjuntos ya aprovisionado.
"${compose[@]}" ps --status running db | grep -q db || {
    echo "PostgreSQL no se encuentra ejecutándose" >&2; exit 1;
}
docker volume inspect fact_central_staging_documentos >/dev/null

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
BACKUP_ROOT="$ROOT/deploy/backups/pre_reset_$stamp"
mkdir -p "$BACKUP_ROOT"
echo "Creando respaldo en $BACKUP_ROOT"

dbfile="$BACKUP_ROOT/postgresql.dump"
"${compose[@]}" exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' > "$dbfile"
test -s "$dbfile" || { echo "Dump de base de datos vacío" >&2; exit 1; }
# Validar estructura del archivo de backup sin escribir en la base existente.
"${compose[@]}" exec -T db pg_restore --list < "$dbfile" > "$BACKUP_ROOT/postgresql_manifest.txt"
test -s "$BACKUP_ROOT/postgresql_manifest.txt"

# Imagen local para leer volumen sin alterar ficheros originales.
docker run --rm --network none \
  -v fact_central_staging_documentos:/documentos:ro \
  -v "$BACKUP_ROOT:/respaldo" \
  alpine:3.21 sh -c 'cd /documentos && tar -czf /respaldo/documentos.tar.gz .'
tar -tzf "$BACKUP_ROOT/documentos.tar.gz" > "$BACKUP_ROOT/documentos_manifest.txt"

git rev-parse HEAD > "$BACKUP_ROOT/git_commit.txt"
sha256sum "$dbfile" "$BACKUP_ROOT/documentos.tar.gz" > "$BACKUP_ROOT/SHA256SUMS"
(cd "$BACKUP_ROOT" && sha256sum -c SHA256SUMS)

cat <<EOF
RESPALDO CREADO: $BACKUP_ROOT
Validado: dump PostgreSQL legible, archivo documental tar legible, SHA256 correcto.
IMPORTANTE: una restauración REAL de PostgreSQL en base aislada aún es obligatoria
antes de cualquier borrado. Este script NO borra ni reinicia datos.
EOF
