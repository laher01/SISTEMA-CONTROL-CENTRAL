#!/usr/bin/env bash
# CI-only drill: ephemeral PostgreSQL service from GitHub Actions; synthetic documents.
set -Eeuo pipefail
umask 077
test "${CI:-}" = true
test "${GITHUB_ACTIONS:-}" = true
test "${FC_RECOVERY_SYNTHETIC_ONLY:-}" = YES
test "${PGHOST:-}" = localhost
test "${PGDATABASE:-}" = fact_central
test "${PGUSER:-}" = fact
work="$(mktemp -d)"
cleanup() {
  if [ -n "${restoredb:-}" ]; then dropdb --if-exists --force "$restoredb" >/dev/null 2>&1 || true; fi
  rm -rf -- "$work"
}
trap cleanup EXIT
restoredb="fact_restore_synthetic_$RANDOM"
python3 - "$work" <<'PY'
import hashlib,json,io,sys,tarfile
from pathlib import Path
p=Path(sys.argv[1]); files={"tenant-a/factura.xml":b"<Invoice>synthetic</Invoice>","tenant-b/guia.pdf":b"%PDF-1.4 synthetic"}
with tarfile.open(p/"docs.tar.gz","w:gz") as t:
 for name,payload in files.items():
  info=tarfile.TarInfo(name);info.size=len(payload); t.addfile(info,io.BytesIO(payload))
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest={"batch":"synthetic-ci","files":{name:{"size":len(data),"sha256":sha(data)} for name,data in files.items()}}
(p/"manifest.json").write_text(json.dumps(manifest))
PY
# Source DB already migrated by the dedicated job: snapshot before restoring anywhere else.
uv run python ../deploy/seed_recovery_relations_ci.py
psql -X -v ON_ERROR_STOP=1 -c "CREATE TABLE synthetic_restore_marker(id integer primary key, tenant text not null)"
psql -X -v ON_ERROR_STOP=1 -c "INSERT INTO synthetic_restore_marker VALUES (1, 'tenant-alpha'), (2, 'tenant-beta')"
docker run --rm --network host --user "$(id -u):$(id -g)" -e PGPASSWORD=fact -v "$work:/backup" "postgres:${FC_CI_PG_MAJOR:?}" pg_dump -h localhost -U fact -d fact_central -Fc -f /backup/database.dump
python3 - "$work" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);manifest=json.loads((p/"manifest.json").read_text())
for key,name in [("database_sha256","database.dump"),("archive_sha256","docs.tar.gz")]:
 manifest[key]=hashlib.sha256((p/name).read_bytes()).hexdigest()
(p/"manifest.json").write_text(json.dumps(manifest))
PY
python3 ../deploy/recovery_pair_audit.py --archive "$work/docs.tar.gz" --dump "$work/database.dump" --manifest "$work/manifest.json" --batch synthetic-ci
createdb "$restoredb"
docker run --rm --network host -e PGPASSWORD=fact -v "$work:/backup:ro" "postgres:${FC_CI_PG_MAJOR:?}" pg_restore -h localhost -U fact --exit-on-error --no-owner --no-acl -d "$restoredb" /backup/database.dump
test "$(psql -XAt -d "$restoredb" -c 'SELECT version_num FROM alembic_version')" = 0038
test "$(psql -XAt -d "$restoredb" -c "SELECT COUNT(*) FROM synthetic_restore_marker")" = 2
FC_DATABASE_URL="postgresql+psycopg://fact:fact@localhost:5432/$restoredb" uv run python ../deploy/validate_restored_relations.py
# Check document bytes after safe inspection; tar extraction targets disposable empty directory.
mkdir "$work/restored-docs"
python3 ../deploy/recovery_safe_extract.py --archive "$work/docs.tar.gz" --manifest "$work/manifest.json" --target "$work/restored-docs"
python3 - "$work" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); m=json.loads((p/"manifest.json").read_text())
for name, spec in m["files"].items():
 data=(p/"restored-docs"/name).read_bytes()
 assert len(data)==spec["size"] and hashlib.sha256(data).hexdigest()==spec["sha256"]
print("SYNTHETIC_DOCUMENT_RESTORE_OK")
PY
export FC_DATABASE_URL="postgresql+psycopg://fact:fact@localhost:5432/$restoredb"
export FC_RECOVERED_DOC_ROOT="$work/restored-docs"
uv run python ../deploy/verify_recovered_storage_ci.py
uv run alembic upgrade 0039
test "$(psql -XAt -d "$restoredb" -c 'SELECT version_num FROM alembic_version')" = 0039
uv run alembic downgrade -1
test "$(psql -XAt -d "$restoredb" -c 'SELECT version_num FROM alembic_version')" = 0038
uv run alembic upgrade 0039
test "$(psql -XAt -d "$restoredb" -c 'SELECT version_num FROM alembic_version')" = 0039
echo "EPHEMERAL_POSTGRES_AND_DOCUMENTS_RESTORE_OK"
test "$(psql -XAt -d "$restoredb" -c "SELECT COUNT(*) FROM synthetic_restore_marker")" = 2
echo "ALEMBIC_0039_REAL_ROUNDTRIP_OK"
export FC_E2E_ISOLATED=true
PYTHONPATH=. uv run python scripts/seed_roles_e2e.py
PYTHONPATH=. uv run python scripts/test_restored_rbac_ci.py
