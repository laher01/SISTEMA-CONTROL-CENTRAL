# MISD — Contrato de eliminación definitiva de documentos y expedientes

**Estado:** especificación funcional acordada; todavía no implementada por completo en el candidato #396.

## Comportamiento solicitado

**Eliminar significa quitar el elemento de la lógica operativa y borrar su archivo físico del almacenamiento. La eliminación es definitiva: no hay papelera ni restauración.** Una carga posterior es un ingreso nuevo, con nuevo identificador y procesamiento desde cero.

### Eliminación individual

Desde **Registros** o **Documentos**, la acción elimina únicamente el elemento seleccionado y se aplica de forma individual. Debe desaparecer de la contabilidad, listados, conteos, pendientes y expedientes operativos; también se eliminan sus datos derivados y vínculos exclusivos.

La auditoría conserva un evento separado y mínimo —tenant, actor, fecha, motivo, identificador/hash y resultado— para dejar evidencia de la operación, pero no conserva una copia recuperable del documento ni mantiene activo el registro contable eliminado.

### Eliminación de un expediente

Al eliminar un expediente, se elimina el expediente completo y todos los documentos que le pertenecen o dependen exclusivamente de él: factura, guías, vouchers y demás adjuntos. Antes de confirmar, la vista previa debe mostrar el expediente y el detalle/cantidad de archivos que se eliminarán.

No se deben eliminar silenciosamente elementos compartidos o vinculados a otros expedientes. Si existen dependencias que no se pueden resolver con seguridad, la operación completa se bloquea y explica el motivo.

### Nueva carga

Después de una eliminación completada, subir nuevamente el mismo archivo crea un ingreso nuevo. No se reactiva el ID anterior ni se recuperan su extracción, relaciones, permisos o estado previo. La carga ejecuta de nuevo OCR, validaciones de identidad fiscal, deduplicación y asignación de ámbito.

## Controles obligatorios

- Validar tenant, propietario/jerarquía, permiso, motivo y alcance exacto en servidor; nunca confiar solo en la selección mostrada por la interfaz.
- Inspeccionar referencias a expedientes, relaciones documentales, GRE, voucher, pagos, liquidaciones y obligaciones de conservación antes de borrar.
- No borrar el archivo físico si otra referencia válida aún lo usa. El almacenamiento está direccionado por tenant y SHA-256, así que la cola debe verificar referencias antes de cada borrado.
- Confirmar el cambio lógico y el evento de auditoría en transacción; borrar bytes después del commit con cola durable, idempotente y reintentable. La interfaz informa “borrado físico pendiente” hasta confirmar el borrado del archivo y presenta cualquier error sin declarar éxito completo.
- Comprobantes fiscales protegidos u otra evidencia sujeta a conservación quedan bloqueados mientras no exista autorización y revisión legal específica. El botón general no sustituye esa autorización.
- No cambiar importes, fórmulas económicas ni registros de pagos como efecto lateral. Si una dependencia financiera impide el borrado, bloquearlo y conservar íntegro el expediente.

## Estado de código comprobado

- En el candidato #396, `DELETE /documentos/{id}` solo asigna `deleted_at`; el archivo permanece.
- El flujo actual ofrece listado/restauración y al volver a subir el mismo SHA puede restaurar el registro anterior. Ambos comportamientos contradicen este contrato para la acción **Eliminar**.
- `AlmacenLocal` guarda por tenant/SHA. El mantenimiento cuenta con lógica de limpieza de archivos, pero la ruta de eliminación individual todavía no cumple el contrato completo de dependencias, auditoría y confirmación física.
- En la rama del PR #396, los cambios P1/P2 de aprobación administrativa y colisión de factura al restaurar aparecen en el código; sus hilos de revisión siguen abiertos. Esa restauración existente no debe confundirse con el nuevo comportamiento definitivo.
- El SHA actual de #396 requiere CI propio. Los resultados 8/8 publicados en comentarios corresponden a otro SHA y no certifican el HEAD vigente.

## Pruebas de aceptación

1. Eliminación individual de un documento elegible: desaparece del registro operativo y de cálculos; archivo físico borrado; auditoría mínima disponible; sin restauración.
2. Eliminación individual bloqueada por permiso, tenant, pago, voucher, GRE, referencia, conservación fiscal o dependencia: sin cambios parciales ni borrado de bytes.
3. Eliminación de expediente: vista previa enumera factura, guías, vouchers y adjuntos; al confirmar, se eliminan todos los elementos exclusivos del expediente.
4. Fallo del trabajador de almacenamiento: queda pendiente reintentable y la interfaz no afirma que terminó.
5. Reingreso del mismo archivo tras eliminación completada: nuevo ID y nuevo procesamiento, sin reutilizar datos contables anteriores.
6. Dos cargas/eliminaciones concurrentes: no crean registros duplicados ni borran un archivo todavía referenciado.
7. Pruebas de migración, integridad de claves foráneas, permisos por rol/tenant, OCR, pantallas y regresión completa en el SHA final.

**Criterio de cierre:** no habilitar el botón como eliminación definitiva hasta que estos casos pasen en el candidato actualizado y su CI. Mantener el PR en borrador; sin merge ni despliegue por esta tarea.
