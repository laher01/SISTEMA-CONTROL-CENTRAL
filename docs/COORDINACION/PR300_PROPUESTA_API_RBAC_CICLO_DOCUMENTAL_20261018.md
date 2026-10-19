# FACT CENTRAL / Gate S — Propuesta de API de ciclo documental v1 (NO IMPLEMENTADA)
Fecha: 18/10/2026. Uso exclusivo de coordinación. Estado: PROPUESTA SUJETA A ACUERDO DE LOS PROPIETARIOS.

## HEAD verificados
PR #286 ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7 (eliminación transaccional). PR #292 61a3a18aa071a2fb1a638ccf2285d3451db1eeba (papelera/restauración). No cambió ninguno desde el análisis anterior.
PR #300 8c66c3b24ba25f7207eceec39e263a1fbaa5230a al inicio de esta revisión: coordination-guardrails SUCCESS; backend, recepción y roles aún in_progress.

## Problema de contrato (observado en código)
#292 invoca `eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)` para retirada por lote; #286 requiere `almacen` y contempla borrado definitivo. Corregir solo la firma no basta: se necesita distinguir efectos recuperables e irreversibles.

## Endpoints recomendados (rutas ilustrativas, no prometidas)
| Verbo/ruta | Semántica | Autorización | Condición de rechazo |
|---|---|---|---|
| `GET /documentos/capacidades?documento_id=<uuid>` | Capacidades por recurso, no rol genérico | Actor/tenant/propietario | Recurso fuera de ámbito → 404 |
| `POST /documentos/{id}/retirar` | Borrado lógico reversible | `documentos.retirar` | Dependencias cuyo estado impide retirar → 409 |
| `POST /documentos/retirar-lote` | Invoca **retirar**, nunca borrado definitivo | `documentos.retirar` por item | ID duplicado 422; por item fuera de ámbito 404/resultado genérico |
| `POST /documentos/{id}/restaurar` | Recuperación mismo registro/archivo | `documentos.restaurar` | Hash ausente/alterado, conflicto documento equivalente o expediente inactivo → 409 |
| `POST /documentos/{id}/solicitar-eliminacion-definitiva` | Solicitud previa sin borrar | `documentos.eliminar_definitivo.solicitar` | Factura/guía emitida, pagos o vínculos protegidos → 409 |
| `POST /documentos/{id}/confirmar-eliminacion-definitiva` | Baja definitiva autorizada y auditada, solo cuando legal y técnicamente permitido | `documentos.eliminar_definitivo.aprobar` + ámbito | Dependencia o token previo inválido → 409 |
| `POST /expedientes/{id}/retirar` | Retirada reversible del conjunto | `expedientes.retirar` | Validaciones cruzadas |
| `POST /expedientes/{id}/restaurar` | Restauración consistente del conjunto | `expedientes.restaurar` | Referencias/huellas inválidas → 409 |

**Compatibilidad:** ningún endpoint actual `DELETE` debe cambiar silenciosamente de baja lógica a definitiva. Planificar transición de clientes existentes: marcar semántica, deprecar donde proceda y probar UI antes de retirar endpoints antiguos. Estos nombres son sugeridos y no autorizan alterar contratos ajenos.

## JSON conceptual de capacidades
```json
{
  "documento_id": "<uuid>",
  "puede_retirar": true,
  "puede_restaurar": false,
  "puede_solicitar_eliminacion_definitiva": false,
  "puede_confirmar_eliminacion_definitiva": false,
  "motivos_bloqueo": ["VINCULO_GRE_ACTIVO"]
}
```
Las capacidades son por acción, recurso, tenant y estado; la API operativa debe repetir autorización dentro de su propia transacción, no confiar en flags previos del frontend.

## Invariantes obligatorios
1. Mismo tenant en expediente, FACT, GRE, voucher, pagos, referencias, líneas UBL, actor y almacenamiento. No confiar en UUID proporcionado.
2. Retirada lógica conserva IDs, archivos, hash, vínculos históricos y auditoría; estados retirados no participan en saldos activos según políticas vigentes.
3. Restauración verifica original y SHA, conflictos de identidad y validez del expediente; una transacción no restaura a medias.
4. Baja definitiva nunca ejecuta un `DELETE` en cadena oculto desde retirada, no altera validez tributaria de comprobantes emitidos, ni destruye auditoría obligatoria. Debe rechazar dependencias externas o requerir procedimiento explícito separado.
5. Reingesta del mismo SHA solo después de estado confirmado, con bloqueo/índices idempotentes y conciliación FS↔DB. Eliminar no significa eliminar legalmente una factura SUNAT.
6. FACT+GRE+VCHR ligados a un expediente no triplican importe; líneas UBL únicas por tenant/documento/número. Documentos pendientes de aprobación no incrementan acumulados.
7. Concurrencia: cualquier decisión depende de validación bajo bloqueo transaccional; reintentos son idempotentes y no exponen archivos de otro tenant.
8. Capacidades SUPERADMIN/gestor/otros roles expresadas por permisos efectivos y ámbitos; no convertir SUPERADMIN en borrador universal por error.

## Contratos para los responsables de otros frentes
- Dueño #286: mantener integridad de FS/DB, bloqueo, eliminación controlada y reingesta; proponer función independiente que no sea invocada por retirada por lote.
- Dueño #292: retirar/restaurar/gestión de papelera, capacidades y UI; invocar operación lógica inequívoca.
- Este Gate S: redactar especificaciones y tests sintéticos, evaluar CI e integración solo en ramas aisladas.
- Aprobación de ambos propietarios antes de planear refactor runtime; **no se ha confirmado su aceptación**.

## Criterios de prueba cruzada sintética
T01 actor gestor dueño retira FACT → mismo registro en papelera, archivo y SHA preservados.
T02 restaura FACT y consultas repetidas → mismo ID, importe una sola vez, ninguna línea duplicada.
T03 lote con 2 documentos y un ID ajeno → aislamiento total, resultado sin filtrar metadatos.
T04 FACT con GRE/VCHR/pago vinculados → baja definitiva rechazada, ningún huérfano.
T05 reingesta mismo archivo tras eliminación controlada y auditoría → no queda fantasma ni doble importe.
T06 dos sesiones PostgreSQL: retirada/reingesta/reescaneo → serialización por tenant, sin pérdidas.
T07 falla tras movimiento de archivo antes de COMMIT → reversión/reconciliación idempotente.
T08 capability true/false comparado contra endpoint real bajo rol y estado; cambios concurrentes revalidados.
T09 expediente completo FACT+GRE+VCHR retira/restaura → consistencia de vínculos, importes y recibos.
T10 migraciones 0024/0035/0041: heads y downgrade probados solo en DB descartable.

## Gate
PR #300 sigue DRAFT. Gate S OPEN. Sin merge, main, VPS, despliegue, migración real ni intervención sobre #286/#292.
