# PR #292 — Auditoría S: pagos, retiradas, permisos y storage

Estado: revisión del módulo MISD en la rama `feat/document-retention-role-actions-20261018`. No autoriza operaciones sobre producción.

## Hallazgos y defensas verificables en código

1. **Rutas alternativas:** `POST /documentos/retirar-lote` reutiliza `eliminar_documento` por cada identificador, por lo que hereda las validaciones de ámbito, plazo de 30 minutos, autorización de cliente, liquidación y voucher. Puede devolver éxito parcial por lote; cada resultado debe mantenerse auditable. Los endpoints directos de documentos y expedientes bloquean GESTOR/USUARIO fuera de ventana.
2. **Uso único y alcance:** `POST /misd/solicitudes/{id}/ejecutar` toma bloqueo de fila para solicitud, expediente y documentos. Requiere tenant, la cuenta original solicitante, la misma identidad de rol/miembro/gestor y el ámbito vigente; consume estado `EJECUTADA` en la misma transacción. El rechazo y la ejecución repetida no alteran los datos.
3. **Vouchers:** un `PagoERP.voucher_documento_id` implica protección aunque el pago sea de otro período. Se añadió comprobación en retiro integral MISD y en `DELETE /expedientes`, además del retiro individual existente.
4. **Originales y conservación:** las retiradas de este ciclo solo actualizan `deleted_at`; no suprimen originales físicos ni los registros de pagos. La cola de mantenimiento requiere controles de referencias, conservación legal y respaldo antes de habilitar una política de destrucción definitiva.
5. **Multi-tenant y jerarquía:** la consulta de solicitud y expediente filtra tenant; la bandeja filtra visibilidad de aprobadores. Las aprobaciones dependen del rol y relaciones vigentes. Cambiar la identidad del solicitante invalida su permiso de ejecutar una autorización anterior.

## Bloqueante de alta prioridad: concurrencia con liquidaciones

El módulo de pagos genera `PagoERP` y otros asientos mediante rutas propias (por ejemplo `backend/app/api/routes/responsable.py`). La operación MISD bloquea el expediente y revisa si ya hay liquidación, pero **no puede garantizar que una transacción de pagos que no tome el mismo bloqueo no inserte una liquidación simultáneamente**.

Por tanto, **no se ha probado ni demostrado** la exclusión mutua real pago/retirada. La prueba de dos restauraciones simultáneas no demuestra esta propiedad.

### Contrato pendiente para el módulo de pagos

- Acordar un lock transaccional común, adquirido en un orden único, por tenant y conjunto de producción/período antes de generar liquidaciones o ejecutar retiro.
- Bajo el mismo lock: recalcular elegibilidad de facturas activas y validar que ninguna solicitud de retiro incompatible está ejecutándose; MISD revalida pagos y cantidades.
- Ejecutar pruebas PostgreSQL con dos transacciones reales, en ambos órdenes (pago primero / retirada primero), verificando ausencia de liquidaciones basadas en producción retirada.
- Conservar pagos, vouchers, auditoría y originales; documentar fallos de transacción y reintentos.

**No modificar rutas de pagos propiedad de otros chats sin verificar responsables y contratos compartidos.** Hasta resolver esta condición, **NO integrar, NO desplegar, NO habilitar destrucción física**.

## Pendientes complementarios

- Validar vigencia de jerarquía del aprobador justo antes de ejecutar una solicitud aprobada (no solo al aprobar).
- Pruebas de concurrencia de `retirar-lote`, controles 403/404 de tenants y consistencia de estados en todas las vistas.
- Proteger documentos fiscales de eliminación física según retención, incluyendo referencias cruzadas incluso retiradas, backups y recuperabilidad.
