# PR #293 — Evidencia funcional de CI (2026-10-18)

## Referencia exacta
- PR: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/293 (DRAFT)
- Commit de código probado: `5b6633e13dc31fe69f2c3d679b97cf7209b89c49`.
- Run backend `39111038202`: **SUCCESS**, con `ruff check`, `ruff format --check`, `mypy app` y `pytest` **SUCCESS**.
- Run recepción documental `39111038107`: **SUCCESS**, con Ruff, mypy, pytest y Alembic upgrade en BD desechable **SUCCESS**.
- Run coordination guardrails `39111038198`: **SUCCESS**.
- Run roles integration `39111038136`: en progreso durante la verificación de este registro; consultar estado final por SHA.

## Defectos hallados y corregidos
1. XML sintético con byte literal no ASCII: `ffb6635f...`.
2. Ruff format en archivos nuevos: `d502c2b...`, `f72a1b8...`.
3. `ResponseValidationError` en test por usar `estado='PENDIENTE'` no admitido por el esquema; se reemplazó por `PENDIENTE_RELACION` en `5b6633e...`.

## Alcance probado
- API: contexto de tenants distintos, lectura y descarga de documentos ajenos rechazadas, confirmación OCR y vinculación cruzada rechazadas, ausencia de mutaciones tras rechazo.
- PostgreSQL real: dos transacciones concurrentes para registrar ítems UBL de un mismo documento y verificar una sola línea y su importe/cantidad tras commit.
- Únicamente datos sintéticos. Son pruebas con inyección de contexto de acceso de test, **no** login/token end-to-end.

## Bloqueos pendientes
- Autenticación E2E entre dos clientes reales de staging, restauración pareada DB/archivos autorizada, rollback, RBAC después del restore, carreras completas de FACT con archivos distintos e idempotencia runtime de eventos NEXUS.
- Gate S **OPEN**. PR #264, #290 y #293 no deben fusionarse ni desplegarse sin gate y revisión independientes. Sin VPS ni alteración de main.
