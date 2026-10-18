# PR #293 — Registro de evidencia OCR / UBL concurrente

Fecha: 2026-10-18. Rama aislada `test/290-ocr-rbac-postgres-20261018`. Gate S **OPEN**.

## Referencias verificadas
- PR #290: 3/3 CI SUCCESS en commit de pruebas `f63f0699e7f2b39504d80c2605e73dc9a28dc448`. Commit documental posterior `916a5a4323b885729eab611a660b8f67fdbf24a4`.
- PR #293: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/293 — DRAFT; rama creada desde PR #290.
- Se añadieron `backend/tests/test_pr290_ocr_document_api_rbac.py` y `backend/tests/test_pr290_ubl_postgres_concurrency.py`.
- CI inicial PR #293: fallo de Ruff por byte literal no ASCII en UBL sintético; corregido en `ffb6635f0434be2cda1f4560cdded6e0cdb80c5b`.
- Segunda validación: fallo de Ruff format en ambos archivos; corregido en `d502c2b0903aca3a909825e226c2d82871d80e06` y `f72a1b8e8b8742272223be934652b4170753a498`.
- Runs activos en última revisión de `f72a1b8e...`: backend `39110832665`, recepción `39110832756`, roles `39110832658`. Ruff y mypy pasados, pytest en progreso para backend y recepción. **Ningún SUCCESS final afirmado aquí.**

## Cobertura nueva (pendiente resultado funcional)
1. Acceso API / documentos de tenant ajeno: lectura y descarga 404, confirmación OCR 404, vinculación 404; comprobación de ausencia de cambios cruzados.
2. Vinculación desde documento propio hacia expediente de tenant B: rechazo 404 y comprobación de ausencia de relación.
3. Consulta autorizada del documento propio de tenant B mediante contexto separado (fixture de pruebas, no flujo completo login real).
4. Dos transacciones PostgreSQL paralelas procesan el mismo UBL: una debe insertar 1 línea y otra 0, con un único importe/cantidad persistidos.

## Límites del alcance
- No confundir fixture de contexto con pruebas end-to-end de token y sesión de autenticación.
- Los nuevos tests no verifican aún simultaneidad de expedientes + múltiples archivos del mismo FACT, ni productor/consumidor runtime NEXUS.
- Sin restore pareado real, no es autorización para staging ni VPS.
- Mantener PR #264 y #290 DRAFT; no editar main, no merge ni despliegue.
