#!/usr/bin/env bash
# Retención conservadora de respaldos de despliegue; nunca borrar respaldos recientes.
set -Eeuo pipefail
umask 077
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
dir="$root/deploy/backups"
test -d "$dir" || exit 0
test ! -L "$dir" || { echo "Directorio de respaldos enlazado: bloqueo" >&2; exit 1; }
# Permitir solo nombres generados por los tres scripts de FACT CENTRAL.
# Preservar siempre los dos respaldos más recientes y sus sumas SHA256 si existen.
mapfile -d '' dumps < <(find "$dir" -maxdepth 2 -type f \( -name 'factcentral_predeploy_*.dump' -o -name 'fact_central_bootstrap_*.dump' -o -name 'fact_central_*.dump' \) -print0)
if (( ${#dumps[@]} < 3 )); then exit 0; fi
mapfile -t newest < <(printf '%s\n' "${dumps[@]}" | while IFS= read -r f; do stat -c '%Y %n' -- "$f"; done | sort -nr | head -n 2 | cut -d' ' -f2-)
for f in "${dumps[@]}"; do
  case "$f" in "$dir"/fact_central_*.dump|"$dir"/audit/factcentral_predeploy_*.dump) ;; *) continue ;; esac
  [[ "$f" == "${newest[0]}" || "$f" == "${newest[1]}" ]] && continue
  # Comprobar antigüedad real; solo archivos regulares sin symlinks y >14 días.
  if [[ -f "$f" && ! -L "$f" ]] && find "$f" -maxdepth 0 -type f -mtime +13 | grep -q .; then
    rm -- "$f"
    [[ ! -L "$f.sha256" && -f "$f.sha256" ]] && rm -- "$f.sha256"
    echo "Respaldo vencido retirado: ${f#"$dir/"}"
  fi
done
