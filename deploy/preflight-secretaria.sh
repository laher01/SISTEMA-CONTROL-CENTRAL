#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
import base64
p = Path('deploy/.env.production')
values = {}
for line in p.read_text().splitlines():
    key, sep, value = line.strip().removeprefix('export ').partition('=')
    if sep and key.strip() in {'FC_CONSULTA_COACTIVA_TOKEN', 'FC_CONSULTAS_EMPRESAS_ENCRYPTION_KEY'}:
        values[key.strip()] = value.strip().strip('"\'')
token = bool(values.get('FC_CONSULTA_COACTIVA_TOKEN'))
try:
    key = len(base64.urlsafe_b64decode(values.get('FC_CONSULTAS_EMPRESAS_ENCRYPTION_KEY', ''))) == 32
except ValueError:
    key = False
print('APIPERU_TOKEN_PRESENTE=' + ('SI' if token else 'NO'))
print('APIPERU_LLAVE_CIFRADO_VALIDA=' + ('SI' if key else 'NO'))
PY
