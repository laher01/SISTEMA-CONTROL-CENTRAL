# Contrato OCR/PDF ↔ MISD 3-2.1 (PR #292)

Estado: **propuesta de integración documental en rama independiente; no desplegada**.
Referencia normativa interna de implementación: `docs/COORDINACION/PR292_CONTRATO_MISD_OCR_PDF_PENDIENTES.md` en PR #292. Si cambia, revisar compatibilidad antes de integrar. El documento del PR #292 es la fuente de autoridad para la operación de retirada.

## Propiedad y responsabilidades

- **OCR/PDF** recibe archivos, extrae texto/datos, clasifica, detecta ilegibilidad/formato no soportado/no pertinencia y expone estados de revisión. No borra físicamente archivos, no ejecuta SQL de eliminación y no determina quién puede retirar documentos.
- **MISD** (PR #292) es el único propietario de la autorización, retirada lógica, restauración, trazabilidad de la operación y futura destrucción física legalmente admisible.
- **La interfaz** muestra el botón *Eliminar* al final de cada pendiente, solo cuando `capacidades.puede_retirar` sea verdadero; la decisión real sigue siendo del servidor en cada petición. La identidad de destino es **UUID**, nunca nombre o número de factura.
- **NEXUS/Gestor** consumen estados y eventos; no implementan borrado paralelo.

## Contratos observados en la rama PR #292

| Operación MISD | Contrato |
| --- | --- |
| Consulta de capacidades | `GET /api/v1/documentos/capacidades`: `puede_retirar`, `puede_restaurar`, `puede_eliminar_definitivamente` |
| Vista previa sin mutación | `POST /api/v1/documentos/previsualizar-retirada` con `{"documentos_ids":["UUID"]}` |
| Retirada lógica individual | `DELETE /api/v1/documentos/{id}` |
| Retirada por lote | `POST /api/v1/documentos/retirar-lote` |
| Consulta de retirados | `GET /api/v1/documentos/retirados` |
| Restauración individual | `POST /api/v1/documentos/{id}/restaurar` |

Respuestas esperadas: `204` retiro exitoso (refrescar bandeja/contadores); `403` sin permisos; `404` inexistente/retirado/fuera de ámbito; `409` conflicto o aprobación pendiente (conservar fila); `422` solicitud inválida (conservar fila). En lotes, inspeccionar respuesta individual antes de actualizar la interfaz.

## Casos de entrada OCR/PDF

- **Ilegible / formato desconocido / archivo no pertinente / subida accidental / pendiente sin expediente**: mantener registro disponible para revisión y, si MISD autoriza, presentar retirada con confirmación y vista previa.
- **OCR fallido** no habilita por sí mismo eliminación automática o física, ni exonera de controles por rol, tenant, vínculos o retención.
- Después de `204`: refrescar pendientes, contadores, búsqueda y vínculos visibles. Una copia de OCR en caché jamás puede reactivar un documento retirado: cualquier reproceso debe verificar su estado vigente y tenant con el backend.
- Ante `403/404/409/422`: no retirar la fila de la interfaz localmente; informar el error y permitir corrección según permisos.

## Permisos (según propuesta PR #292)

`SECRETARIA` y `SUPERADMIN` no retiran. `ADMINISTRADOR`, `GERENTE`, `RESPONSABLE`, `USUARIO` y `GESTOR` están sujetos a ámbito y reglas server-side. Receptor autorizado y solicitante no administrador: conflicto `409` hasta autorización; el circuito persistente de solicitud/aprobación/notificación **no existe todavía**.

## No implementado / prohibiciones

- Eliminación física definitiva: **deshabilitada** hasta política de conservación fiscal, autorización, referencias compartidas, respaldo y auditoría.
- No introducir endpoints o permisos de borrado en OCR. El futuro flujo de solicitud/aprobación pertenece exclusivamente a MISD.
- No incorporar importes/relaciones de documento fallido o pendiente a totales sin validación del módulo competente.
- No integrar este contrato como funcionalidad productiva hasta pruebas cruzadas con PR #292.

## Criterios de aceptación cruzados

1. PDF ilegible y formato desconocido, ambos con/sin expediente: solo MISD puede retirar; solo bajo UUID, rol y tenant permitidos.
2. SECRETARIA/SUPERADMIN: botón oculto y endpoint `403`; usuario fuera de ámbito: sin retirada.
3. Receptor autorizado + no administrador: `409`, estado conservado.
4. Retirada lógica `204`: no aparece en pendientes activos, sin eliminación física; auditable y restaurable por MISD cuando corresponda.
5. Restauración: respetar originales, integridad hash, dependencias y duplicados.
6. Reprocesamiento OCR posterior a retirada: no resucitar ni revincular registros retirados.
7. Verificar regresión backend/frontend/roles en ambiente aislado antes de cualquier merge.

## Auditoría cruzada contra PR #292 (19/10/2026)

Cotejo de la rama MISD `feat/document-retention-role-actions-20261018`, HEAD consultado `84fb3b82`, con rutas OCR actuales. **Hallazgos, no implementación ni permiso de desplegar**.

| Criterio | Evidencia | Estado |
| --- | --- | --- |
| `GET capacidades` | Campos `puede_retirar`, `puede_restaurar`, `puede_eliminar_definitivamente=false` | Implementado en rama |
| `POST previsualizar-retirada` | UUID de 1 a 100, tenant, ámbito, respuestas apto/no disponible, sin mutación | Parcial: no ejecuta los bloqueos de receptor autorizado, liquidación y voucher que sí verifica `DELETE` |
| `DELETE /{id}` | `deleted_at`, auditoría, protección por ámbito y receptor, bloqueo liquidaciones/vouchers, recálculo y commit | Implementado como retirada lógica |
| `POST retirar-lote` | Invoca retirada individual y devuelve resultados por registro | Implementado; la UI debe comprobar éxitos y rechazos por UUID, no solo el status HTTP del lote |
| `GET retirados` y `POST restaurar` | Ámbito, tenant; restaurar verifica archivo original, SHA256 y colisión activa | Implementado en rama |
| Pendientes — botón | `Pendientes.tsx` consulta capacidades, muestra botón al final y usa UUID; confirmación menciona conservación del original | Implementado en rama |
| Caché OCR | `cache_ocr.procesar_con_cache` clave por tenant, SHA256 y versión; extracción técnica, sin autorización fiscal | Protección parcial: función de caché no valida `deleted_at` porque no recibe el documento. Verificar en todos los *call sites* que no pueda reprocesarse documento retirado ni revincularlo por procesos asíncronos |
| Estado de ilegible/no reconocido | OCR emplea `REVISION_REQUERIDA`/`FALLIDO` y bandeja Pendientes | Requiere pruebas de integración: sin expediente, documento erróneo y casos con bloqueo |
| Eliminación física | `puede_eliminar_definitivamente=false`, original conservado en retirada | No implementada/habilitada |

### Discrepancias y acciones asignadas

1. **MISD #292:** corregir `previsualizar-retirada` para aplicar **los mismos bloqueos de negocio** que `DELETE`, sin mutaciones, o distinguir explícitamente `APTO_PRELIMINAR` de `APTO_RETIRADA`. Así, un `aptos` positivo no induce a pensar que habrá autorización final.
2. **OCR/PDF + integración MISD:** auditar invocaciones de `_procesar_y_aplicar`, tareas por lote y restauración para demostrar que `deleted_at` y tenant se validan antes de leer caché o generar relaciones, incluso si la retirada ocurre entre selección y ejecución. El caché por sí solo no constituye ese control.
3. **MISD #292 / UI:** probar respuesta parcial de `retirar-lote`; ningún `NO_RETIRADO` debe desaparecer de Pendientes por refresco optimista.
4. **Pruebas cruzadas:** documento ilegible sin expediente, tipo no reconocido, subida accidental, receptor autorizado, liquidación/voucher protegidos, roles, otro tenant, borrado y reprocesamiento concurrentes.
5. **Interfaz y rotulación:** el texto `Eliminar` representa actualmente una **retirada lógica**, no borrado físico; confirmar que la UX no sugiera destrucción irreversible.

**Frontera obligatoria:** todos los endpoints de retirada/restauración y su autorización pertenecen a MISD #292; OCR no debe añadir eliminación SQL o física ni crear un flujo alternativo. No fusionar ni desplegar sin cerrar las regresiones.
