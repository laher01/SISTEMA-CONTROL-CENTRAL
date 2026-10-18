# PR #264 — Auditoría de integración Trabajo 10 OCR / NEXUS 2.0

Fecha de revisión: 2026-10-17. **Solo inventario y contratos; no modifica funcionalidades ni ejecuta VPS, staging, fusión o despliegue.**

## Referencias verificadas
- `main` SHA `75e84c5d69ae1662d99e1ef671898586e2157f15`.
- PR **#277 fusionado** (merge commit `82e9d2ec0308e49a24d701e29d84add2a4882314`), 14 archivos: ruta documentos; automatización; extracción de campos; servicios nuevos `lotes_imagenes.py` y `transferencias_bcp.py`; pruebas; documentación; pantalla `Subir.tsx`.
- PR **#275 v2**, `d217f27c3e95ab10d3ad4df0bd8eb9401b06f050`, **abierto / draft / no fusionado**. La lista de 14 rutas coincide con #277, pero eso **no prueba igualdad de contenido ni ausencia de commits divergentes**. Exigir comparación git de tree/merge-base y diff antes de integrar.
- PR **#264** es auditor de recuperación **draft**, no es una rama de integración OCR. Mantener sus límites y no incorporar cambios de runtime OCR en él.
- Captura proporcionada del workflow `Despliegue` indica pasos exitosos para `verificación-backend`, `Verify-frontend` y `Despliegue`, e imprime «FACT CENTRAL desplegado correctamente» / «Commit VPS verificado: 75e84c5d69ae1662d99e1ef671898586e2157f15». Es evidencia visual de un **run reportado exitoso**, no inspección remota propia, ni garantía de pruebas OCR end-to-end en VPS.

## Contratos efectivos y especificaciones pendientes
- En `main`, `POST /api/v1/documentos/lote-imagenes` acepta de 1 a 10 imágenes por solicitud, con validación de firma JPEG/PNG/WEBP/TIFF y resultados individualizados `ok/duplicado/error`, reusa auth, tenant y ruta ordinaria de carga. **No agrupa páginas de una factura y no equivale a cola de OCR de lotes ilimitados**.
- `lotes_imagenes.py` implementa `dividir_sublotes` y `decidir_factura`: estados `CREATED`, `REJECTED_DUPLICATE`, `CONFLICT_REVIEW`, `REVIEW_REQUIRED`; la función no inserta en BD ni implementa transacciones.
- `transferencias_bcp.py` sugiere campos de transferencia BCP; no convierte el voucher en factura ni acredita pago bancario.
- `docs/OCR_CORE_V1.md` documenta `POST /api/v1/documentos/{id}/procesar`, `PUT /api/v1/documentos/{id}/extraccion-confirmada`, `POST /api/v1/documentos/{id}/crear-expediente`, y almacenamiento de procedencia/confianza en `datos_extraidos.procesamiento_documental`.
- `docs/CORE/08_CORE_INTEGRATION_CONTRACTS.md` exige esperar evento `storage.file.available` antes de OCR/clasificación; correlación, tenant, idempotencia y auditoría.
- `docs/INGESTA_IMAGENES_LOTES_OCR_V1.md` todavía se autodenomina **especificación**, incluye contratos `/api/v1/ingestas/lotes` como **propuestos, no existentes por definición**; contempla ZIP/RAR solo bajo descompresión aislada y segura.
- El OCR y NEXUS deben integrarse **mediante eventos y resultados persistidos** con `tenant_id`, `ingestion_id`, `file_id`, `documento_id`, `expediente_id`, `correlation_id`, `event_version`, confianza y evidencias; NEXUS solo propone, no concede acciones tributarias irreversibles sin permisos/confirmación.

## Decisiones y diferencias por resolver
1. La especificación de ingreso inteligente indica `REJECTED_DUPLICATE` sin segundo expediente; el contrato OCR Core también contempla **reutilizar expediente y vincular evidencia**. Debe definirse la distinción explícita entre (a) archivo idéntico reingresado, (b) nuevo archivo con identidad fiscal igual, (c) documento complementario, (d) identidad coincidente con montos/receptor diferentes. Exigir no duplicar efecto económico y no contaminar expedientes.
2. `lotes_imagenes.py` deriva la identidad fiscal de emisor/tipo/serie/número/tenant; `OCR_CORE_V1.md` menciona receptor en clave de búsqueda. Confirmar unicidad física de BD, índice, locks, tratamiento de distinta razón social, colisiones y condiciones de carrera.
3. Examinar Alembic actual y migraciones realmente presentes después de la fusión; los 14 archivos del PR #277 no incluyen archivo de migración nuevo. Eso no demuestra que no existan migraciones previas relevantes.
4. Validar API de sublotes con 1/10/11 imágenes, mezcla válidas/duplicadas/error, rutas tenant, límites por bytes realmente leídos, RBAC y reintentos idempotentes.
5. Confirmar extracción de factura, GRE remitente/transportista, vouchers, cotizaciones y OC con documentos sintéticos; evidencias por campo, correcciones humanas, fechas, importes, líneas y asociaciones. No inferir cobertura total por el despliegue exitoso.
6. No introducir documentos de un tenant en expediente de otro. Validar idempotencia por `tenant_id`, hashes y claves fiscales; event replay y auditoría.
7. Mantener compatibilidad con NEXUS sin exigir que OCR dependa de NEXUS para operar. Proponer contrato versionado y consumer idempotente; ninguna orden automática irreversible.

## Plan de pruebas y siguiente paso (solo rama aislada)
A. Crear matriz documental y pruebas contractuales en rama de integración separada, basada en `main` vigente; no reutilizar PR #264 como rama OCR.
B. Ejecutar diff real #275 vs #277/main y reconciliar PRs sin cherry-pick ciego.
C. Pruebas de clasificación, asociaciones, duplicados bajo concurrencia, RUC/serie/fecha/importe contradictorios, RBAC de dos tenants, API sublotes, eventos, rollback y migraciones.
D. CI backend/frontend + PostgreSQL 16/17 donde corresponda, reportar SHA exacta y fallos.
E. Revisar compatibilidad del esquema con recovery gate S del PR #264, sin mezclas ni accesos remotos.

**Gate S OPEN, integración I y despliegue D bloqueados según PR #264.** Una captura de despliegue no autoriza un nuevo acceso al servidor.
