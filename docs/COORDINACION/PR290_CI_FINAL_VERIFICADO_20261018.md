# PR #290 — CI final comprobado — 18/10/2026

**Rama:** `test/264-ocr-rbac-tenant-items-20261018`  
**Commit probado:** `f63f0699e7f2b39504d80c2605e73dc9a28dc448`  
**Estado:** los 3 workflows terminaron `SUCCESS`, sin nuevos defectos reportados por CI.

| Workflow | Run ID | Conclusión | Evidencias de pasos |
|---|---:|---|---|
| backend | 39110275540 | SUCCESS | Ruff check, Ruff format, mypy, pytest: SUCCESS |
| recepcion-documental-ci | 39110275644 | SUCCESS | Ruff check, Ruff format, mypy, pytest, Alembic upgrade en BD desechable y migration heads: SUCCESS |
| roles-real-integration | 39110275538 | SUCCESS | Job integration: SUCCESS |

Los primeros runs del PR #290 fallaron por `ruff format --check`. El commit `f63f0699` corrigió el formato y CI ya lo verificó.

## Alcance real / límites
- Nueva regresión de API para dos tenants, carga de mismos bytes y prohibición de lectura cruzada; nueva comprobación de idempotencia de líneas UBL y catálogo separado por tenant.
- Los pasos pytest completos aprobaron en backend y recepción. No se presupone un resultado de restauración de backups reales ni despliegue de staging por ello.
- La prueba actual de tenant alterna los contextos sintéticos de sesión mediante fixture; no equivale a autenticación de credenciales reales de extremo a extremo ni a cobertura completa de extracción OCR, descarga, vinculación, edición y expediente fiscal.
- No prueba carrera concurrente de líneas UBL con dos transacciones ni redelivery del runtime NEXUS.
- Gate S sigue OPEN hasta verificación de respaldos pareados, rollback, RBAC posterior a restauración y entorno autorizado.

**Política:** PR #290 sigue DRAFT; no fusionar ni desplegar, sin modificar #264, main ni VPS.