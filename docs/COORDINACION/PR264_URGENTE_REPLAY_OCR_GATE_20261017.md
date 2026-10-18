# URGENTE+ — Revisión OCR/NEXUS, idempotencia y seguridad (17/10/2026)

## CI de partida confirmado
PR #264 HEAD `867bf7aea6878ad09e1a7ae9e5eb03f39a1f9d93`: 6/6 workflows **success**, incluidos PostgreSQL 16/17, FastAPI roles, backend, recepción y restauración sintética offline.

## Pruebas añadidas (solamente en el PR de seguridad)
- `deploy/test_recovery_pair_audit.py`: ejecutar la inspección del mismo TAR sintético dos veces da el mismo inventario, no modifica el hash SHA-256 del archivo ni introduce estados nuevos.
- Se rechaza manifiesto de inventario vacío si el TAR contiene documentos.

Estas verificaciones prueban idempotencia de **lectura del auditor de backups**, no idempotencia del bus de eventos OCR/NEXUS, ni duplicados contables reales.

## Contratos verificados en código y documentación existente
- OCR integrado en `main` después del PR #277, con `POST /api/v1/documentos/lote-imagenes` (1–10 archivos tratados individualmente; no agrupa páginas).
- `docs/OCR_CORE_V1.md`: procesamiento `POST /api/v1/documentos/{id}/procesar`, confirmación por `PUT /api/v1/documentos/{id}/extraccion-confirmada`, creación/vinculación `POST /api/v1/documentos/{id}/crear-expediente`.
- `docs/CORE/08_CORE_INTEGRATION_CONTRACTS.md`: OCR solo después de `storage.file.available`, deduplicación de consumidores por tenant/id de evento y auditoría.
- La función `lotes_imagenes.decidir_factura` devuelve decisiones fiscales conservadoras y no constituye por sí misma una restricción UNIQUE en PostgreSQL.
- Los 14 blobs modificados por PR #275 son idénticos a los correspondientes de main: prohibido duplicar o aplicar sus commits a ciegas.

## Pendientes de FINALIZAR
1. En rama de integración OCR–NEXUS separada, probar emit/consume/replay real con dos tenants, idempotencia por evento, autenticación, permisos RBAC y expedientes fiscales.
2. Confirmar restricciones únicas transaccionales para identidades de factura; la política de documentos duplicados vs evidencia adicional debe tener comportamiento único y auditable.
3. Verificar que GRE, voucher y OC no creen hechos económicos sin comprobante validado.
4. Gate S exige backup pareado y restauración independiente de BD+archivos en staging verdaderamente aislado, con revisión de permisos, SHA256, Alembic, limpieza ante fallos e informe firmado.

**PR264 DRAFT, S OPEN, I/D BLOCKED. Sin VPS, merge ni despliegue.**
