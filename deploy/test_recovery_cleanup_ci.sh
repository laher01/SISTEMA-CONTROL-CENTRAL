#!/usr/bin/env bash
# Verifies trap-based cleanup under an injected failure in disposable CI resources.
set -Eeuo pipefail
test "${GITHUB_ACTIONS:-}" = true
test "${FC_RECOVERY_SYNTHETIC_ONLY:-}" = YES
test "${PGHOST:-}" = localhost
test "${PGUSER:-}" = fact
tempdir="$(mktemp -d)"
db="fact_cleanup_synthetic_$RANDOM"
createdb "$db"
set +e
(
 set -Eeuo pipefail
 trap 'dropdb --if-exists --force "$db" >/dev/null 2>&1; rm -rf -- "$tempdir"' EXIT
 touch "$tempdir/sentinel"
 echo "INJECTED_FAILURE_FOR_CLEANUP_CHECK"
 exit 91
)
status=$?
set -e
test "$status" = 91
test ! -e "$tempdir"
test "$(psql -XAt -d fact_central -c "select count(*) from pg_database where datname='$db'")" = 0
echo "INTERRUPTION_CLEANUP_VERIFIED"
