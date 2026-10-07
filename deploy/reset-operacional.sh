#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/docker-compose.production.yml"
ENV_FILE="$ROOT_DIR/deploy/.env.production"
BACKUP_DIR="$ROOT_DIR/deploy/backups"

cd "$ROOT_DIR"

test -f "$ENV_FILE" || { echo "Falta $ENV_FILE"; exit 1; }
mkdir -p "$BACKUP_DIR"

compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

echo "FACT CENTRAL - RESET OPERACIONAL"
echo
echo "Se eliminarán:"
echo "  - documentos"
echo "  - expedientes"
echo "  - alertas"
echo "  - empresas creadas por la operación"
echo "  - auditoría operativa"
echo "  - archivos almacenados en /data/documentos"
echo
echo "Se conservarán:"
echo "  - tenant/organización"
echo "  - miembros/usuarios"
echo "  - gestores"
echo "  - cuentas de acceso"
echo "  - sesiones de acceso"
echo
read -r -p 'Escribe RESET-FACT-CENTRAL para continuar: ' CONFIRMACION
if [ "$CONFIRMACION" != "RESET-FACT-CENTRAL" ]; then
  echo "Cancelado."
  exit 1
fi

echo "Verificando base de datos..."
"${compose[@]}" up -d db >/dev/null

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$BACKUP_DIR/reset_previo_$timestamp.dump"
echo "Creando respaldo: $backup"
"${compose[@]}" exec -T db sh -c   'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$backup"

echo "Deteniendo servicios de aplicación..."
"${compose[@]}" stop tunnel frontend backend >/dev/null || true

echo "Limpiando datos operativos..."
"${compose[@]}" exec -T db sh -c '
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL
BEGIN;
TRUNCATE TABLE alertas, documentos, expedientes, empresas, auditoria CASCADE;
COMMIT;
SQL
'

echo "Vaciando almacenamiento documental..."
"${compose[@]}" run --rm --no-deps backend sh -c   'find /data/documentos -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +'

echo "Levantando FACT CENTRAL..."
"${compose[@]}" up -d --remove-orphans

echo
echo "RESET OPERACIONAL COMPLETADO"
echo "Respaldo guardado en: $backup"
echo "La organización y los accesos se conservaron."
