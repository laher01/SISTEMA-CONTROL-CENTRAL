# MISD — Contrato propuesto de eliminación integral y conservación (PR #292)

**Estado:** propuesta de diseño; NO habilita borrado físico, SQL DELETE ni limpieza de archivos reales. Fecha: 2026-10-23. Propietario: MISD. OCR/PDF, contabilidad, GRE y Etapa 7 no ejecutan eliminación por su cuenta.

## Fuente y brecha verificada
- `docs/COORDINACION/PR292_CONTRATO_MISD_OCR_PDF_PENDIENTES.md`: retirar lógico, restaurar, previsualizar y `puede_eliminar_definitivamente=False`; eliminación física pendiente. Parte del documento afirma pendientes que pudieron evolucionar: contrastar código y CI actual.
- `backend/app/models.py`: `Expediente`, `Documento.ruta_storage`, `ReferenciaGRE.documento_id`, `PagoERP.voucher_documento_id`, `SolicitudRetiroMISD` y archivos adjuntos con `archivo_ruta`.
- `backend/app/services/misd_pagos.py`: liquidaciones por período/tenant y voucher vinculado a `PagoERP` son bloqueantes actuales.
- `backend/app/api/routes/solicitudes_retiro_misd.py`: retiro lógico de expediente y documentos, con permiso, ámbito, solicitud consumible, aprobación, auditoría y bloqueo financiero PostgreSQL; NO borra originales.
- No existe todavía evidencia documental suficiente de todas las relaciones GRE transportista/remitente ni de plazos legales de conservación. No afirmar que la ausencia de una FK aislada acredita independencia.

## Principio y alcance
**Intención operativa:** si se autoriza una eliminación definitiva legalmente válida, limpiar todos los derivados exclusivos del elemento en registros operativos y almacenamiento gestionado, no solo ocultar el expediente. **No implica destruir auditoría legal, comprobantes tributarios, pagos, respaldos protegidos ni documentos sujetos a fiscalización.** Donde haya retención legal, bloqueo de pago, requerimiento, hold o respaldo inmutable, usar retirada lógica o bloqueo hasta vencimiento/autorización; una eliminación física protegida queda expresamente prohibida.

## Matriz de decisiones (objetivo; no implementado)

| Objeto | Previsualización y dependencias | Operación admisible |
|---|---|---|
| Expediente | Recorrer documentos, facturas, guías, vouchers, OCR, referencias GRE, relaciones contables, solicitudes, exportaciones y archivos físicos; distinguir exclusivos y compartidos | Retirada lógica integral primero. Depuración física **solo** si todos los hijos elegibles, sin referencias/hold y después de aprobación. Bloquear lote integral si un hijo protegido impide completarlo; no dejar eliminación parcial silenciosa |
| Factura | Identificar guías, notas, anexos, voucher, pagos, GRE, conciliaciones y documentos del mismo expediente | No eliminar factura antes de procesar dependencias exclusivas. Un hijo protegido o compartido impide eliminación física; no borrar documentos de terceros por cascada |
| Guía remitente | Confirmar vínculos reales con GRE transportista, manifiestos, movimientos y expedientes | Guía con transportista vinculada: no depurar físicamente hasta resolver la relación y obligaciones. Sin transportista: elegible solo tras verificar demás dependencias y conservación |
| Voucher | Consultar `PagoERP.voucher_documento_id`, otras conciliaciones y referencias económicas | **Relacionar un voucher no autoriza borrarlo**: el vínculo con pago es bloqueo vigente; mantener evidencia financiera mientras exista obligación; retirar/depurar solo voucher no protegido y sin referencias |
| Otros documentos/OCR | Verificar expedientes, anexos, revisiones y archivo compartido | Retirar lógicamente; depurar físicamente si sin referencia, conservación, hold y con aprobación independiente |
| Archivos en almacenamiento | Verificar ruta normalizada dentro del tenant, hash, propietario, copias o referencias compartidas y estado en objetos externos | Borrado idempotente del objeto elegible; conservar evidencia mínima de operación sin secretos ni contenido fiscal |

## Contrato de previsualización propuesto
Antes de cambiar estados devolver: `tenant_id`, `objetivo_id`, `tipo`, `modo_solicitado`, árbol de dependencias (IDs, tipo, exclusivo/compartido, motivo bloqueo), estado de conservación, referencias de pago/GRE, recuentos de blobs, tamaño estimado y `decision` = `APTO_LOGICO` / `APTO_FISICO` / `BLOQUEADO`; no exponer datos de otros tenants. La autorización y evaluación se repiten en servidor **en el momento de ejecutar**, nunca confiar en un preview antiguo.

## Protocolo de eliminación física futura (no implementado)
1. Requerir rol autorizado + aprobación distinta del solicitante, motivo y validación de tenant; proteger especialidades SUPERADMIN/SECRETARIA según política vigente.
2. Comprobar matriz legal aplicable y obligaciones fiscales, retención, denuncias/litigios, auditoría y holds. Sin política legal verificada => no depurar.
3. Adquirir lock financiero de tenant, locks de filas y revalidar liquidaciones/vouchers/GRE/conservación con la misma transacción.
4. Construir manifiesto firmado por identificadores internos, hashes, tamaño, almacenamiento y referencias; inmovilizar los objetos elegibles y registrar trabajo idempotente con estados `PENDIENTE`, `EN_PROCESO`, `TERMINADO`, `ERROR_RECUPERABLE`. La salida de DB y filesystem requiere patrón outbox/worker y reconciliación: **no prometer atomicidad entre SQL y archivos**.
5. Separar datos funcionales purgables y evidencias de auditoría legalmente conservables; evitar cascadas por FK sin inventario completo. La eliminación física nunca borra pagos ni movimientos contables protegidos.
6. Borrar objetos únicos verificados tras estado durable, aplicar retención de copias según política, corroborar inexistencia y cerrar trabajo; errores deben conservar registro y permitir reintento seguro. No manipular respaldos inmutables fuera de su ciclo establecido.
7. Registrar actor, autorización, alcance, hash del manifiesto, estado, errores, resultado de validaciones y fecha. Proteger rutas contra traversal, enlaces simbólicos y acceso entre tenants.

## Pruebas obligatorias antes de habilitar
- Tenant cruzado en preview, solicitud, aprobación, ejecución y storage; UUID conocido no otorga acceso.
- Factura con hijos exclusivos y compartidos; bloqueo por hijo protegido; sin cascadas a otros expedientes.
- GRE con y sin transportista vinculada; verificar referencias a ambos extremos.
- Voucher enlazado a pago no se elimina, incluso si el operador lo solicita; pagos/responsables/gestores conservan integridad.
- Conservación tributaria, hold, revocación de aprobador, documentos no fiscales sin referencias.
- Concurrencia retiro/pago, doble ejecución, fallo después de transacción DB, fallo de storage, retries, crash/recovery.
- Archivo duplicado con hash compartido, rutas fuera de raíz, copias/restauración desde backup aislado.
- Alembic upgrade/downgrade e integridad referencial, auditoría, OCR y regresión de todos los permisos.
- No ensayar purga real en VPS ni datos de producción. Usar datos sintéticos en almacenamiento y base aislados, con recuperación comprobada.

## Pendientes de coordinación y seguridad
1. Inventariar FK, vínculos GRE y adjuntos mediante consultas de solo lectura y tests; asignar propietarios de GRE, contabilidad y storage.
2. Jurídico/tributario define categorías, plazo y evidencia que nunca se elimina; no inferir plazos.
3. Aprobar por separado la política de purga, el plan de backup/retención y las modificaciones de código.
4. Implementar en otro PR MISD independiente; NO editar landing de Etapa 7 ni cambiar API de OCR sin coordinación.
5. Mantener P1/P2 y cuestiones de PR #341 sin resolver hasta aprobación real.
