#!/usr/bin/env bash
# Inspección de solo lectura: no despliega, no migra, no cambia servicios.
set -Eeuo pipefail
DEPLOY_DIR="$(pwd -P)"
cd "$DEPLOY_DIR"
echo "FACT CENTRAL | preflight Secretaría"
echo "UTC: $(date -u +%FT%TZ)"
echo "Commit VPS: $(git rev-parse HEAD)"
echo "Rama VPS: $(git branch --show-current)"
echo "Estado local:"
git status --porcelain
# Permitir exclusivamente archivos operativos no rastreados de esta VPS.
# Cualquier cambio a archivos versionados sigue bloqueando la instalación.
check_worktree() {
  local line path
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [[ "${line:0:2}" != "??" ]]; then
      echo "Cambio local versionado: $line" >&2
      return 1
    fi
    path="${line:3}"
    case "$path" in
      actualizar-fact-central.sh|deploy/auto-update.log|deploy/local-backups/*|deploy/private/*|deploy/.deploy.lock|deploy/backups/*)
        echo "Archivo operativo local preservado: $path" ;;
      *)
        echo "Archivo local no reconocido: $path" >&2
        return 1 ;;
    esac
  done < <(git status --porcelain --untracked-files=all)
}

if ! check_worktree; then
  echo "::error::VPS presenta cambios no autorizados; bloquear despliegue."
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
# Validar antes de crear un respaldo que las herramientas de verificación estén disponibles.
for herramienta in git flock pg_restore; do
  if ! command -v "$herramienta" >/dev/null 2>&1; then
    echo "::error::Falta herramienta necesaria para despliegue: $herramienta"
    exit 1
  fi
done
echo "Almacenamiento de respaldos:"
if [ -d deploy/backups ]; then
  find deploy/backups -maxdepth 1 -type f -name 'fact_central_*.dump' -printf '%TY-%Tm-%Td %TH:%TM %s bytes\n' | tail -n 5
else
  echo "No hay directorio de respaldos"
fi
echo "Preflight de solo lectura completado: NO valida restauración, NO certifica backups."
