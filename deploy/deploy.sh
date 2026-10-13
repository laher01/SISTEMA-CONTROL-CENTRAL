#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$DEPLOY_DIR/deploy/docker-compose.production.yml"
ENV_FILE="$DEPLOY_DIR/deploy/.env.production"
BACKUP_DIR="$DEPLOY_DIR/deploy/backups"

cd "$DEPLOY_DIR"
exec 9>"$DEPLOY_DIR/deploy/.deploy.lock"
flock -n 9 || { echo "Ya existe otro despliegue en ejecución"; exit 1; }

test -f "$ENV_FILE" || { echo "Falta $ENV_FILE"; exit 1; }
mkdir -p "$BACKUP_DIR"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "El repositorio de la VPS tiene cambios locales. Se cancela el despliegue para no sobrescribirlos." >&2
  git status --short
  exit 1
fi

# Comprobación de seguridad antes de modificar el árbol de trabajo.
bash "$DEPLOY_DIR/deploy/preflight-secretaria.sh"

# Respaldo obligatorio antes de cualquier actualización.
compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
if ! "${compose[@]}" ps --status running db | grep -q db; then
  echo "Base PostgreSQL detenida: se bloquea la actualización." >&2
  exit 1
fi
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$BACKUP_DIR/fact_central_$timestamp.dump"
"${compose[@]}" exec -T db sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$backup"
if [ ! -s "$backup" ]; then
  echo "No se produjo un respaldo PostgreSQL válido." >&2
  exit 1
fi
# Verificar integridad estructural del formato custom sin restaurar en producción.
if ! "${compose[@]}" exec -T db pg_restore --list < "$backup" >/dev/null; then
  echo "Respaldo PostgreSQL inválido; abortar antes de actualizar" >&2
  exit 1
fi
echo "Respaldo PostgreSQL creado: $backup"

previous_commit="$(git rev-parse HEAD)"
git fetch origin main
git checkout main
git pull --ff-only origin main
current_commit="$(git rev-parse HEAD)"

if [ -n "${EXPECTED_COMMIT:-}" ] && [ "$current_commit" != "$EXPECTED_COMMIT" ]; then
  echo "Commit desplegado inesperado: $current_commit; esperado: $EXPECTED_COMMIT" >&2
  exit 1
fi

echo "Actualizando FACT CENTRAL: $previous_commit -> $current_commit"

"${compose[@]}" build --pull
"${compose[@]}" up -d --remove-orphans

for _ in $(seq 1 30); do
  if curl --fail --silent --show-error http://127.0.0.1:18080/health >/dev/null; then
    "${compose[@]}" ps
    echo "FACT CENTRAL desplegado correctamente en $current_commit"
    exit 0
  fi
  sleep 2
done

"${compose[@]}" ps
"${compose[@]}" logs --tail=100 backend frontend tunnel
echo "El despliegue no superó la comprobación de salud" >&2
exit 1
