# OCR ↔ MISD: concurrencia entre procesamiento y retirada

Auditoría estática de `backend/app/api/routes/documentos.py` y `backend/app/services/cache_ocr.py`. Rama del PR #318; sin despliegue.

## Controles observados

- `_documento(session, tenant_id, documento_id)` rechaza documento ausente, fuera de tenant o con `deleted_at`.
- `procesar-pendientes` filtra documentos por tenant, alcance y `deleted_at IS NULL` **al seleccionar**.
- `procesar_con_cache` solo devuelve datos técnicos por tenant, hash y versión; no decide estado fiscal ni eliminación.
- PR #318 agrega un `session.refresh(documento)` y control `deleted_at` en el punto compartido `_procesar_y_aplicar`, antes de reutilizar el resultado previo o extraer por caché.

## Carrera residual NO RESUELTA

T1 procesa documento activo, luego inicia OCR costoso; T2 MISD retira el documento y confirma; T1 continúa, aplica vínculos/automatización y confirma cambios. El control de entrada por sí solo **no impide** esta ventana de carrera.

No introducir una transacción larga bloqueando filas durante OCR sin evaluar impacto. Contrato recomendado para una solución coordinada: (1) extracción técnica sin cambios fiscales, (2) adquirir bloqueo de fila o comparar versión de documento en transacción corta de aplicación, (3) comprobar de nuevo tenant, `deleted_at` y alcance, (4) aplicar relaciones de forma atómica, (5) asegurar que MISD adquiere bloqueo compatible al retirar, (6) pruebas multisesión con sincronización de eventos y rollback. La operación MISD sigue siendo propiedad exclusiva del PR #292.

## Criterios pendientes

- En los tres flujos (individual, lote y caché reutilizada), comprobar que documento retirado antes de la aplicación no genera expediente, vínculo ni suma.
- Dos sesiones y retirada durante extracción, sin reactivación posterior.
- Sin pérdida de aislamiento por tenant ni de auditoría MISD.
- `409` para conflicto o reintento idempotente, definido conjuntamente con MISD.
- No fusionar hasta que CI de PR #318 sea satisfactorio y se diseñe la coordinación transaccional sin efectos fiscales inesperados.
