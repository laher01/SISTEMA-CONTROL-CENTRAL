# PR #264 — Auditoría de pruebas PostgreSQL y RBAC OCR/NEXUS

Fecha: 2026-10-18. Solo evidencia y planificación de pruebas, sin modificación de runtime OCR ni uso de VPS.

## Estado comprobado
- PR #264 DRAFT SHA `9be609f1000eab85bd6b816826b7f066fb53d147`: seis workflows terminados SUCCESS (coordination, paired restore offline, PG16/17 synthetic, backend, recepción documental y roles).
- PR #277 integrado en main. PR #275 DRAFT con los 14 blobs revisados idénticos a main; no duplicar código.

## Código real revisado en main
- `backend/tests/test_cotizaciones_concurrencia.py`: `test_huella_comercial_concurrente_postgresql` usa `ThreadPoolExecutor`, `Barrier` y dos sesiones reales PostgreSQL para disputar `Documento.huella_comercial`. Afirma un commit y un duplicado con `IntegrityError`; **esto valida cotizaciones (COT), no unicidad fiscal de facturas**.
- En el mismo archivo, `test_api_importacion_semantica_simultanea_postgresql` ejercita peticiones HTTP concurrentes a `/api/v1/documentos/paquete` con PDFs sintéticos y comprueba duplicados comerciales.
- `backend/tests/test_permisos_actores_tenants.py`: `test_usuario_no_contacta_persona_de_otro_tenant` comprueba contactos/chat ajenos (404/no listado); `test_ningun_actor_cliente_puede_listar_tenants_globales` exige 403 y `test_admin_tenant_no_puede_crear_superadmin` exige 403. **Son pruebas RBAC reales de chat, directorio y administración, no acceso cruzado a expedientes OCR**.
- `backend/app/services/ingesta.py`: filtros de documento por `tenant_id` y SHA-256, validaciones de expediente tenant y `ComprobanteYaRegistrado`.
- `backend/app/services/automatizacion_documental.py`: validación automática auditada y filtros de `tenant_id` sobre factura/expediente.
- Búsqueda de `storage.file.available` en código por GitHub devolvió solo documentación; no se acreditó el productor/consumidor runtime NEXUS. Buscar alternativas y eventos existentes antes de programar un bus nuevo.

## Pruebas pendientes prioritarias para rama OCR–NEXUS separada
1. Dos sesiones PostgreSQL crean simultáneamente el mismo comprobante fiscal de mismo tenant con diferente hash de archivo: comprobar una única identidad/expediente y efecto económico; inspeccionar constraints/index Alembic antes de definir test.
2. Dos tenants repiten misma serie/número/emisor: comprobar aislamiento de documentos/expedientes vía API usando dos credenciales reales sin contaminación y sin denegar operación legítima de otro tenant.
3. Evento de OCR reentregado fuera de orden: `event_id`, `correlation_id`, versión y deduplicación, sin efecto contable duplicado. No afirmar bus operativo antes de demostrar productor/consumer real.
4. Rechazar confirmación/vinculación por rol no autorizado; campos OCR incompletos o contradictorios a revisión; GRE/voucher/cotización sin crear factura inventada.
5. Mantener las pruebas reales existentes de cotizaciones, pero no citarlas como prueba de simultaneidad fiscal de facturas.

## Gate S
Continúan pendientes respaldo pareado de DB+documentos de idéntico lote en staging autorizado/aislado, validación RBAC tras restauración, integridad SHA256, rollback y limpieza segura. S OPEN; I y D BLOCKED. PR #264 debe seguir DRAFT. No acceder a VPS, modificar main, fusionar, desplegar ni editar PRs ajenos.
