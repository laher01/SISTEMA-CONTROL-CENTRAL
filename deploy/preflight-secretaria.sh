#!/usr/bin/env bash
# Inspección de solo lectura: no despliega, no migra, no cambia servicios.
set -Eeuo pipefail
DEPLOY_DIR="$(pwd -P)"
cd "$DEPLOY_DIR"
echo "FACT CENTRAL | preflight Secretaría"
echo "UTC: $(date -u +%FT%TZ)"
echo "Commit VPS: $(git rev-parse HEAD)"
echo "Rama VPS: $(git branch --show-current)"
echo "Estado local (resumen, sin revelar contenido privado):"
git status --short
# Los archivos no rastreados se conservan. Solo bloquear cambios versionados.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "::error::Hay modificaciones versionadas en VPS; se bloquea el despliegue."
  exit 1
fi
# La comparación contra el árbol de destino permite detectar colisiones reales.
if [ -n "${EXPECTED_COMMIT:-}" ]; then
  case "$EXPECTED_COMMIT" in
    *[!0-9a-fA-F]*|"") echo "::error::SHA destino inválido."; exit 1 ;;
  esac
  git fetch --quiet origin main
  if ! git cat-file -e "${EXPECTED_COMMIT}^{commit}" 2>/dev/null; then
    echo "::error::Commit destino no disponible."; exit 1
  fi
  if ! git merge-base --is-ancestor HEAD "$EXPECTED_COMMIT"; then
    echo "::error::El commit VPS no es ancestro de destino; requiere revisión."; exit 1
  fi
  # Git advierte y protege frente a colisiones con ficheros sin seguimiento.
  # Se anticipa la comprobación sin modificar el árbol de trabajo.
  python3 - "$EXPECTED_COMMIT" <<'PY'
import os
import subprocess
import sys

target = sys.argv[1]
changed = subprocess.check_output(
    ["git", "diff", "--name-only", "-z", "--diff-filter=ACMR", "HEAD", target]
).split(bytes([0]))
untracked = subprocess.check_output(
    ["git", "ls-files", "--others", "--exclude-standard", "-z"]
).split(bytes([0]))
incoming = {os.fsdecode(p) for p in changed if p}
collisions = []
for raw in untracked:
    if not raw:
        continue
    name = os.fsdecode(raw)
    if name in incoming or any(name.startswith(p + "/") for p in incoming):
        collisions.append(name)
if collisions:
    print("::error::Conflicto con archivos locales no rastreados; no se sobrescribirá nada.")
    for item in collisions:
        print("::error::Conflicto: " + item)
    sys.exit(1)
print(f"Sin colisiones: {len([x for x in untracked if x])} archivos locales conservados.")
PY
fi
echo "Uso de disco:"
df -h "$DEPLOY_DIR"
echo "Espacio disponible (KB):"
df -Pk "$DEPLOY_DIR" | awk 'NR==2 {print $4}'
if [ "$(df -Pk "$DEPLOY_DIR" | awk 'NR==2 {print $4}')" -lt 2097152 ]; then
  echo "::error::Menos de 2 GiB libres: bloquear despliegue."
  exit 1
fi
# Inventario informativo; no implica capacidad suficiente para respaldos nuevos.
if [ -d deploy/backups ]; then
  backup_bytes="$(du -sb deploy/backups | awk '{print $1}')"
  echo "Ocupación actual de backups (bytes): $backup_bytes"
fi
if [ ! -s deploy/.env.production ]; then
  echo "::error::No se encontró archivo de configuración de producción."
  exit 1
fi
echo "Servicio backend:"
if ! curl --fail --silent --show-error --max-time 10 http://127.0.0.1:18080/health >/dev/null; then
  echo "::error::Backend no saludable antes de desplegar."
  exit 1
fi
if ! command -v docker >/dev/null; then
  echo "::error::Docker no encontrado."
  exit 1
fi
docker compose version
# Margen conservador: tres respaldos del tamaño lógico de PostgreSQL más
# 2 GiB para construcción. Bloquear ante errores de consulta o espacio.
compose=(docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml)
database_bytes="$("${compose[@]}" exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select pg_database_size(current_database())"' </dev/null)"
[[ "$database_bytes" =~ ^[0-9]+$ ]] || { echo "::error::No se obtuvo tamaño válido de PostgreSQL"; exit 1; }
free_bytes="$(df -PB1 "$DEPLOY_DIR" | awk 'NR==2 {print $4}')"
[[ "$free_bytes" =~ ^[0-9]+$ ]] || { echo "::error::No se obtuvo espacio libre"; exit 1; }
minimum_bytes=$(( 3 * database_bytes + 2147483648 ))
echo "Capacidad calculada (libre/requerida, bytes): $free_bytes / $minimum_bytes"
if (( free_bytes < minimum_bytes )); then
  echo "::error::Espacio insuficiente para tres respaldos estimados y construcción"
  exit 1
fi
echo "Almacenamiento de respaldos:"
if [ -d deploy/backups ]; then
  find deploy/backups -maxdepth 1 -type f -name 'fact_central_*.dump' -printf '%TY-%Tm-%Td %TH:%TM %s bytes\n' | tail -n 5
else
  echo "No hay directorio de respaldos"
fi
echo "Preflight de solo lectura completado: NO valida restauración, NO certifica backups."
