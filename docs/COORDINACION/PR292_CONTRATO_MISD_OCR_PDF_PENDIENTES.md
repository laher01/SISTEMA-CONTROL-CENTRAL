# Contrato intermodular — MISD 3-2.1 / OCR y PDF 10-2.0

**Propietario de eliminaciones:** MISD (PR #292). **Productor y consumidor:** OCR y PDF — Ingreso de Documentos.

## Principio de propiedad exclusiva
OCR/PDF puede recibir, procesar y mostrar documentos pendientes, ilegibles, formatos no reconocidos o archivos subidos por error; **no debe ejecutar sentencias SQL de borrado ni eliminar archivos del almacenamiento**. Solo MISD autoriza y ejecuta operaciones, conserva auditoría y protege referencias.

## Contratos existentes

- `GET /api/v1/documentos/capacidades`: informa `puede_retirar`, `puede_restaurar` y `puede_eliminar_definitivamente` según rol. La autorización concreta se valida **en el servidor** para cada documento.
- `POST /api/v1/documentos/previsualizar-retirada` con `{"documentos_ids": ["UUID"]}`: resultado de aptitud por documento, **sin mutaciones**.
- `DELETE /api/v1/documentos/{id}`: retira lógicamente un documento del ámbito del rol; registra auditoría y recalcula expediente cuando corresponde.
- `POST /api/v1/documentos/retirar-lote`: reutiliza el mecanismo individual e informa por documento.
- `GET /api/v1/documentos/retirados` y `POST /api/v1/documentos/{id}/restaurar`: bandeja y recuperación según permisos.

El botón **Eliminar** aparecerá al final de cada pendiente visible solo si `capacidades.puede_retirar` es verdadero. Debe operar por UUID del documento, no por nombre de archivo ni número de factura. El mismo botón puede aplicarse a documentos pendientes cuyo OCR falló; el backend decidirá si se permite el retiro.

## Reglas de autorización MISD

- SECRETARIA y SUPERADMIN no pueden retirar documentos ni expedientes.
- ADMINISTRADOR, GERENTE, RESPONSABLE, USUARIO y GESTOR: acceso sujeto al ámbito y controles del servidor.
- Receptor autorizado: el retiro por un rol no administrador se bloquea hasta autorización administrativa formal. Actualmente responde HTTP 409; **el circuito persistente de solicitudes y notificaciones está pendiente**.
- Un documento pendiente sin expediente también debe respetar el ámbito; no debe inferirse el permiso solo por su estado OCR.
- La retirada actual es **lógica**. La eliminación física definitiva permanece deshabilitada hasta establecer conservación legal, referencias, cadena de auditoría, respaldo y autorización.

## Código de respuesta y experiencia de OCR/PDF

- `204`: retiro aceptado; refrescar lista de pendientes y contadores.
- `403`: rol sin permiso.
- `404`: no existe, ya retirado o está fuera del ámbito autorizado.
- `409`: conflicto o autorización pendiente; mostrar mensaje, no quitar el ítem.
- `422`: solicitud inválida; no cambiar la lista.

**No cambiar unilateralmente los contratos**: futuras operaciones `solicitar-eliminacion` y `aprobar-eliminacion` serán responsabilidad del PR #292 y deberán incorporarse con pruebas de compatibilidad.

## Pendientes del PR #292

Solicitud persistente y aprobación por ADMINISTRADOR, migración Alembic, notificación interna, previsualización integral de dependencias, eliminación física legalmente admisible, pruebas de pendientes sin expediente y regresión con estados OCR. No modificar OCR/NEXUS en este PR.
