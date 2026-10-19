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
