# PR #294 — Gate S: verificación de CI, relaciones documentales y NEXUS

Fecha: 2026-10-18. **Gate S OPEN. Sin merge, VPS ni despliegue.**

## CI verificado
Commit autenticación real `a0826dfd643a41eb2ce38ea9d59e255077f77aa3`: cuatro workflows SUCCESS:
- backend `39140636582`: Ruff check, Ruff format, mypy y pytest SUCCESS.
- recepcion-documental-ci `39140636503`: Ruff, mypy, pytest y Alembic DB desechable SUCCESS.
- roles-real-integration `39140636765`: SUCCESS.
- coordination-guardrails `39140636548`: SUCCESS.

La prueba usa POST /api/v1/auth/login, cookies y resolución de sesión desde BD para dos tenants y datos sintéticos: no accede a VPS.

## Relación FACT–GRE–voucher–ítems
Se añadieron pruebas `backend/tests/test_pr294_gre_provisional_integrity.py` para verificar:
1. Registrar dos veces la misma referencia de factura desde GRE deja una única `ReferenciaGRE` y no fabrica factura/importe/ítems.
2. Un mismo expediente puede tener factura, GRE y voucher (`VCHR`) sin crear un segundo expediente ni aumentar `importe_total`.

**Importante:** estos casos verifican invariantes sintéticas y NO constituyen aún la prueba integral de una factura UBL auténtica seguida de GRE y voucher ingresados mediante API ni de una conciliación de ítems en ambas representaciones.

Código observado: `app/services/ingesta.py` filtra por tenant e ingesta por SHA/fiscal; `registrar_referencia_gre` persiste referencia provisional; `app/services/referencias_gre.py` exige referencias explícitas y controla ambigüedad; `app/api/routes/contabilidad_items.py` filtra `LineaComprobanteItem`, Documento y Expediente por tenant.

## Auditoría runtime NEXUS
Búsqueda GitHub en rama por defecto:
- `event_id`: resultados principalmente `docs/AI/24_EVENT_CATALOG.md`, `docs/CORE/05_EVENT_BUS_CONSISTENCY_PROTOCOL.md`, `docs/CORE/08_CORE_INTEGRATION_CONTRACTS.md`.
- `storage.file.available`: resultados en `docs/CORE/08_CORE_INTEGRATION_CONTRACTS.md` y `docs/INGESTA_IMAGENES_LOTES_OCR_V1.md`.
- NEXUS eventos: numerosas referencias en `docs/futuro/nexus/`.

No apareció evidencia suficiente de productor + consumidor runtime con persistencia e idempotencia de eventos. **No marcar NEXUS event bus como funcional** hasta encontrar código ejecutable y verificar reentrega, orden y deduplicación. No agregar bus especulativo.

## Bloqueos físicos staging
- Respaldo coordinado y consistente de PostgreSQL + archivos, mismo corte, manifiesto SHA256, prueba de integridad y custodia.
- Restauración sobre staging segregado autorizado, Alembic sobre respaldo real, RBAC después de restaurar, trazabilidad factura/GRE/voucher/ítems.
- Prueba de rollback completo y limpieza segura sin impacto en producción.
- Revisión de servicios/secretos/HTTPS/monitorización/healthchecks.
- Gate S y autorización responsable. PR #264, #290, #293, #294 DRAFT sin tocar main.

## CI posterior a tests GRE
Commit de código más reciente al generar nota: `9df4fd79922377667442e33821a22d76b02eaec7`. GitHub Actions `39141503072` backend, `39141502969` recepción, `39141502945` roles, `39141503064` guardrails. **No declarar aprobación final mientras terminen**; CI del commit anterior `a0826dfd` no cubre tests GRE nuevos.
