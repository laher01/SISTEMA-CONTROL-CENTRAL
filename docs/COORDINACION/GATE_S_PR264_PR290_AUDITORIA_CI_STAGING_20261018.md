# Gate S — auditoría cruzada PR #264 y #290 (2026-10-18)

> Estado verificado: **S OPEN; sin permiso de staging real, merge o despliegue VPS**. Esta evidencia no reemplaza la autorización de un responsable. Revisión read-only de CI y PR; documento en rama release aislada.

## Identificadores inmutables
- PR #264: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/264 ; DRAFT/open; HEAD `4c0fc3259f73ded1ce307901e43908ee0b86ff4c`; base `integration/208-main-review-20261017`.
- PR #290: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/290 ; DRAFT/open; HEAD `233ce895e8db97d92d246445dee480a08de222ce`; base `release/264-gate-s-readiness-20261018`.
- PR #290 modifica solo `backend/tests/test_pr264_ocr_tenant_items_isolation.py`; ninguna cobertura puede declararse aprobada antes de superar format check y ejecutar tests.

## Evidencia positiva #264 (todos SUCCESS para HEAD indicado)
| Run | Workflow | Resultado / alcance |
| --- | --- | --- |
| 39101196038 | coordination-guardrails | SUCCESS |
| 39101196049 | security-paired-restore-dry-run | SUCCESS; auditor local/offline y archivo sintético; no recuperación VPS |
| 39101196053 | security-synthetic-postgres-restore-ci | SUCCESS; PG16 + PG17 restauración sintética y roundtrip Alembic 0039 |
| 39101196052 | recepcion-documental-ci | SUCCESS |
| 39101196039 | security-fiscal-concurrency-pr264 | SUCCESS; competencia de transacciones PostgreSQL por identidad Expediente FACT |
| 39101196034 | roles-real-integration | SUCCESS; no equivale a RBAC completo OCR |
| 39101196051 | backend | SUCCESS |

## CI #290 — bloqueo concreto y evidencias
| Run | Workflow | Resultado |
| --- | --- | --- |
| 39108921171 | recepcion-documental-ci | FAILURE: step `uv run ruff format --check .` |
| 39108921154 | backend | FAILURE: step `uv run ruff format --check .` |
| 39108921209 | roles-real-integration | SUCCESS |

Las pruebas nuevas del PR #290 **no están acreditadas como aprobadas**. Las dos fallas de formato pueden impedir alcanzar pruebas posteriores; corregir y reconsultar logs/resultados antes de concluir.

## Lista exacta para obtener una versión candidata a staging (orden y salida requerida)
1. [ ] **CI #290**: aplicar Ruff al archivo test nuevo en su propia rama; reejecutar workflows backend/recepcion; adjuntar runs SUCCESS y resultados de pytest; no declarar tests ejecutados solo porque CI pasa fase de formato.
2. [ ] **Cobertura RBAC API**: usuario tenant A y usuario tenant B separados; validar GET/listado/descarga, POST vincular, PUT confirmar extracción y acciones de expediente: acceso propio permitido y ajeno 403/404; registrar respuestas y verificar que no haya cambios DB cruzados.
3. [ ] **Expediente fiscal por tenant**: dos tenants con igual emisor/receptor/serie/correlativo; ambas creaciones legítimas independientes, lectura/relación cruzada denegada. Usar datos sintéticos.
4. [ ] **Ítems UBL**: reingesta/reproceso y operaciones concurrentes con bytes diferentes para mismo FACT; validar exactamente un expediente, una factura principal y líneas/importe contabilizado una vez. Requerir PostgreSQL real y assertions posteriores a commit/rollback.
5. [ ] **OCR/NEXUS**: verificar contrato runtime productor/consumidor existente antes de agregar eventos; después probar retransmisión, `event_id`, `correlation_id`, desorden y deduplicación sin efectos fiscales duplicados. Si no hay bus real, registrar gap y excluir función de staging.
6. [ ] **Staging autorizado y segregado**: inventario de base/archivos/secretos/red/credenciales; confirmar que no puede escribir en producción y no usa datos personales fuera de un entorno aprobado.
7. [ ] **Respaldo consistente pareado**: DB + archivos del mismo punto consistente, manifiesto SHA256, muestras reconciliadas y registro del operador.
8. [ ] **Restore + migración + RBAC postrestore**: restaurar copia real autorizada en staging aislado, verificar asociaciones factura–GRE–voucher–ítems; probar Alembic y recuperación/rollback, retención y eliminación segura.
9. [ ] **Verificación operacional**: Docker/healthcheck backend, arranque, migraciones, secretos, certificado HTTPS, logs sin datos sensibles, monitorización, alertas y pruebas de rollback en staging.
10. [ ] **Revisión final**: CI en el SHA candidato, revisión de diffs/base, permisos y aprobaciones humanas, checklist firmado para decidir si puede **desplegarse en staging**. Integración a main y producción quedan como hitos independientes posteriores.

## No hacer
- No ejecutar SSH, no tocar VPS, no fusionar #264/#290 ni editar otros PR.
- No cambiar OCR de `main`, ni presentar restauración sintética como recuperación real.
- No declarar un sistema listo para producción por 7/7 CI del PR #264.

## Próxima decisión técnica
Prioridad inmediata: arreglar Ruff en PR #290 y conseguir los logs de pytest. En paralelo diseñar los casos API tenant/RBAC pendientes. Mantener ambos DRAFT.
