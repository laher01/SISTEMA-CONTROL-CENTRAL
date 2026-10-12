#!/usr/bin/env bash
# Inspección de solo lectura: no despliega, no migra, no cambia servicios.
set -Eeuo pipefail
DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEPLOY_DIR"
echo "FACT CENTRAL | preflight Secretaría"
echo "UTC: $(date -u +%FT%TZ)"
echo "Commit VPS: $(git rev-parse HEAD)"
echo "Rama VPS: $(git branch --show-current)"
echo "Estado local:"
git status --porcelain
if [ -n "$(git status --porcelain)" ]; then
  echo "::error::VPS tiene cambios locales: bloquear despliegue."
  exit 1
fi
echo "Uso de disco:"
df -h "$DEPLOY_DIR"
echo "Espacio disponible (KB):"
df -Pk "$DEPLOY_DIR" | awk 'NR==2 {print $4}'
if [ "$(df -Pk "$DEPLOY_DIR" | awk 'NR==2 {print $4}')" -lt 2097152 ]; then
  echo "::error::Menos de 2 GiB libres: bloquear despliegue."
  exit 1
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
echo "Almacenamiento de respaldos:"
if [ -d deploy/backups ]; then
  find deploy/backups -maxdepth 1 -type f -name 'fact_central_*.dump' -printf '%TY-%Tm-%Td %TH:%TM %s bytes\n' | tail -n 5
else
  echo "No hay directorio de respaldos"
fi
echo "Preflight de solo lectura completado: NO valida restauración, NO certifica backups."
