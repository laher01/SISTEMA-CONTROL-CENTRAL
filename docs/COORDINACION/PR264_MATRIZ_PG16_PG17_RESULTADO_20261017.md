# PR #264 — Consolidación de matriz PostgreSQL 16/17 y gate S

Fecha: 2026-10-17.

## Matriz verificada
Workflow único `.github/workflows/security-synthetic-postgres-restore-ci.yml` ejecuta el mismo guion `deploy/ci_synthetic_pg_restore.sh` para PG 16 y PG 17 con clientes `pg_dump`/`pg_restore` de versión correspondiente. Run matriz **39085878912: pg-restore (16) SUCCESS, pg-restore (17) SUCCESS**.

Cada variante incluye: base efímera, pg_dump/pg_restore, tabla de marcador con dos registros conservados, dos documentos recuperados con SHA256/rutas y expediente/tenant, Alembic 0038→0039→0038→0039, autenticación FastAPI y RBAC con cuentas sintéticas, y fallo inducido con limpieza comprobada. El anterior workflow sólo PG17 se ha eliminado **después** de comprobar ambas variantes. Los tests offline continúan en `security-paired-restore-dry-run`.

## Límites
No constituye prueba en staging remoto. El workflow de CI trabaja con datos sintéticos y un PostgreSQL temporal del runner. Los traps no protegen por sí solos ante SIGKILL o caída de host. La evidencia de staging exige aislamiento verificable y snapshots coordinados.

## Checklist
Véase `docs/COORDINACION/PR264_STAGING_PAIRED_RESTORE_CHECKLIST_20261017.md`. El protocolo requiere autorización independiente de operación, fuentes del mismo lote, comparación documental sin datos privados, verificaciones RBAC y Alembic sobre el staging **restaurado**, rollback y limpieza de recursos.

**S sigue abierta, I y D bloqueados. Nada se ha fusionado ni desplegado.**
