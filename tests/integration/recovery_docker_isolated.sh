#!/usr/bin/env bash
# CI-only integration rehearsal using synthetic PostgreSQL data and disposable Docker volumes.
set -Eeuo pipefail
test "${CI:-}" = "true" || { echo "CI only"; exit 1; }
command -v docker >/dev/null
scratch="$(mktemp -d)"
suffix="fc-recovery-${GITHUB_RUN_ID:-$$}"
db="${suffix}-db"; volume="${suffix}-pg"; docs="${suffix}-docs"
cleanup() { docker rm -f "$db" >/dev/null 2>&1 || true; docker volume rm "$volume" "$docs" >/dev/null 2>&1 || true; rm -rf "$scratch"; }
trap cleanup EXIT
docker volume create "$volume" >/dev/null
docker volume create "$docs" >/dev/null
docker run -d --name "$db" -e POSTGRES_PASSWORD=synthetic -e POSTGRES_USER=sample -e POSTGRES_DB=sample -v "$volume:/var/lib/postgresql/data" postgres:17-bookworm >/dev/null
# pg_isready can succeed against the temporary bootstrap server which then shuts
# down. Wait for initdb to finish and for the final server to answer real SQL.
wait_sql() {
  local database="$1"
  local result
  for i in $(seq 1 60); do
    if result="$(docker exec "$db" psql -X -v ON_ERROR_STOP=1 -At -U sample -d "$database" -c 'SELECT 1' 2>/dev/null)" && [[ "$result" == "1" ]]; then
      return 0
    fi
    sleep 1
  done
  echo "PostgreSQL did not become SQL-ready for $database" >&2
  docker logs "$db" >&2 || true
  return 1
}
wait_initdb() {
  local logs
  for i in $(seq 1 60); do
    logs="$(docker logs "$db" 2>&1 || true)"
    if [[ "$logs" == *'PostgreSQL init process complete; ready for start up'* ]]; then
      return 0
    fi
    sleep 1
  done
  echo "PostgreSQL initialization did not finish" >&2
  docker logs "$db" >&2 || true
  return 1
}
wait_initdb
wait_sql sample
docker exec "$db" psql -v ON_ERROR_STOP=1 -U sample -d sample -c 'CREATE TABLE synthetic_tenant_documents (tenant_id text NOT NULL, document_id text PRIMARY KEY, payload text NOT NULL);'
docker exec "$db" psql -v ON_ERROR_STOP=1 -U sample -d sample -c "INSERT INTO synthetic_tenant_documents VALUES ('alpha','doc-a','alpha-only'),('beta','doc-b','beta-only');"
docker run --rm -v "$docs:/documents" alpine:3.20 sh -c "mkdir -p /documents/alpha /documents/beta; printf 'alpha-file' > /documents/alpha/a.pdf; printf 'beta-file' > /documents/beta/b.pdf"
docker run --rm -v "$docs:/documents:ro" -v "$scratch:/backup" alpine:3.20 sh -c 'cd /documents && tar cf /backup/documents.tar . && cd /backup && sha256sum documents.tar > documents.sha256'
docker exec "$db" pg_dump -U sample -d sample --format=custom > "$scratch/postgresql.dump"
test -s "$scratch/postgresql.dump"
(cd "$scratch"; sha256sum postgresql.dump > database.sha256)
(cd "$scratch"; sha256sum -c documents.sha256 database.sha256)
# Simulate failure by removing synthetic rows/files, then restore to another isolated database/volume.
docker exec "$db" psql -v ON_ERROR_STOP=1 -U sample -d sample -c 'TRUNCATE synthetic_tenant_documents;'
docker run --rm -v "$docs:/documents" alpine:3.20 sh -c 'rm -f /documents/alpha/a.pdf /documents/beta/b.pdf'
docker exec "$db" createdb -U sample recovered
docker exec -i "$db" pg_restore -U sample -d recovered --no-owner --no-acl --exit-on-error < "$scratch/postgresql.dump"
rows="$(docker exec "$db" psql -At -U sample -d recovered -c "SELECT string_agg(tenant_id || ':' || document_id, ',' ORDER BY tenant_id) FROM synthetic_tenant_documents;")"
test "$rows" = "alpha:doc-a,beta:doc-b"
docker run --rm -v "$docs:/documents" -v "$scratch:/backup:ro" alpine:3.20 sh -c 'cd /documents && tar xf /backup/documents.tar && test "$(cat alpha/a.pdf)" = alpha-file && test "$(cat beta/b.pdf)" = beta-file'
# Recreate container with same disposable volumes and verify durability.
docker rm -f "$db" >/dev/null
docker run -d --name "$db" -e POSTGRES_PASSWORD=synthetic -e POSTGRES_USER=sample -e POSTGRES_DB=sample -v "$volume:/var/lib/postgresql/data" postgres:17-bookworm >/dev/null
wait_sql recovered
test "$(docker exec "$db" psql -At -U sample -d recovered -c 'select count(*) from synthetic_tenant_documents')" = 2
echo "ISOLATED_PG_RESTORE_OK DOCUMENT_VOLUME_RESTORE_OK CONTAINER_RECREATE_OK SYNTHETIC_TENANT_ROWS_OK"
