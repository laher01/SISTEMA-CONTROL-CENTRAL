#!/usr/bin/env bash
# PR140: isolated deployment to legacy VPS. Must be run over authenticated SSH.
set -Eeuo pipefail
ROOT="$(pwd -P)"
cd "$ROOT"
: "${EXPECTED_COMMIT:?Commit obligatorio}"
: "${DEPLOY_BRANCH:?Rama obligatoria}"
[[ "$DEPLOY_BRANCH" == "integration/document-capture-main-20261011" ]] || { echo "Rama no autorizada" >&2; exit 1; }
[[ "$EXPECTED_COMMIT" =~ ^[0-9a-f]{40}$ ]] || exit 1
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
      actualizar-fact-central.sh|deploy/auto-update.log|deploy/local-backups/*|deploy/private/*)
        echo "Archivo operativo local preservado: $path" ;;
      *)
        echo "Archivo local no reconocido: $path" >&2
        return 1 ;;
    esac
  done < <(git status --porcelain --untracked-files=all)
}

check_worktree || { echo "Árbol local con cambios no autorizados" >&2; exit 1; }
[[ -f deploy/.env.production ]] || exit 1
[[ "$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')" -ge 2097152 ]] || { echo "Disco insuficiente" >&2; exit 1; }
if systemctl is-active --quiet factcentral-update.timer 2>/dev/null; then
  echo "Actualizador de main activo en esta VPS: deshabilitar con procedimiento autorizado antes de desplegar otra rama" >&2
  exit 1
fi
curl -fsS --max-time 10 http://127.0.0.1:18080/health >/dev/null
exec 9>deploy/.deploy.lock
flock -n 9 || { echo "Otro despliegue en curso"; exit 1; }
compose=(docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml)
"${compose[@]}" ps --status running db | grep -q db || { echo "PostgreSQL no disponible"; exit 1; }
git fetch origin "+refs/heads/$DEPLOY_BRANCH:refs/remotes/origin/$DEPLOY_BRANCH"
[[ "$(git rev-parse "origin/$DEPLOY_BRANCH")" == "$EXPECTED_COMMIT" ]] || { echo "SHA diferente al aprobado"; exit 1; }
previous="$(git rev-parse HEAD)"
mkdir -p deploy/backups
backup="deploy/backups/fact_central_$(date -u +%Y%m%dT%H%M%SZ)_pr140.dump"
"${compose[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$backup"
[[ -s "$backup" ]] || { echo "Backup vacío"; exit 1; }
pg_restore --list "$backup" >/dev/null || { echo "Backup ilegible"; exit 1; }
echo "BACKUP_VALIDADO: $backup"
git checkout --detach "$EXPECTED_COMMIT"
echo "DEPLOY_PREVIOUS=$previous DEPLOY_TARGET=$EXPECTED_COMMIT"
"${compose[@]}" build --pull
"${compose[@]}" up -d --remove-orphans
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 5 http://127.0.0.1:18080/health >/dev/null; then
    echo "DESPLIEGUE_VALIDADO=$EXPECTED_COMMIT"
    "${compose[@]}" ps
    exit 0
  fi
  sleep 2
done
"${compose[@]}" ps
echo "Healthcheck falló; requiere recuperación supervisada y revisar migraciones; respaldo: $backup" >&2
exit 1
