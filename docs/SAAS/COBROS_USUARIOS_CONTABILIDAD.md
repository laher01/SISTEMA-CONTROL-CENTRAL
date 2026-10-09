# Cobros del Responsable al Usuario y Contabilidad del Usuario

Estado: especificación técnica para implementación en rama de trabajo; **no desplegar sin pruebas**.

## Alcance y jerarquía
`RESPONSABLE -> USUARIO -> GESTOR`. La cartera solo se consulta o modifica dentro del mismo tenant. Cada Responsable administra el porcentaje de PAGO exclusivamente de Usuarios cuyo `responsable_id` sea su propio `miembro_id`. El porcentaje de COBRO del Responsable no es ese campo: se calcula por factura según agente de retención. La cuenta Usuario solo lee las tasas y sus movimientos; Gestor no accede a esta contabilidad. Administración supervisa con permisos explícitos y auditoría. El porcentaje del Usuario (`Miembro.porcentaje_produccion`) NO es el porcentaje de comisión del Gestor (`Gestor.porcentaje_comision`).

La página `/pago-gestores` existente es una obligación del Usuario hacia sus Gestores, y no equivale a cobros del Responsable ni a ingresos recibidos.

## Base económica
Para cada Usuario, mes calendario y moneda:
- **Fuente única de producción y comisiones**: TODOS los expedientes/facturas ingresados al sistema por Gestores del Usuario, con importe real y sin duplicaciones. Agrupar por `Expediente.gestor_id`, `Expediente.usuario_id`, período, moneda y receptor. No usar pedidos proyectados ni limitar a documentos ya cobrados como base de comisión; no computar carga repetida de una factura.
- **Clasificación de cada factura**: comprobar si la empresa receptora es agente de retención en el contexto operativo pertinente. El modelo `Empresa.agente_retencion` existe, pero antes de calcular se debe validar el criterio de identificación, la vigencia y la fuente del dato para el período facturado. Conservar clasificación snapshot en la liquidación.
- **Cobro del Responsable al Usuario**: sumatoria de importes de facturas cuyo receptor es agente de retención × **3,00 %** + sumatoria de importes de facturas cuyos receptores NO son agentes de retención × **3,50 %**. La tasa se aplica por factura, no sobre un total indiferenciado. Responsable no usa aquí `Miembro.porcentaje_produccion`.
- **Pago del Responsable al Usuario**: base de la producción ingresada por sus Gestores × porcentaje previamente asignado al Usuario por Responsable en el sistema existente (`Miembro.porcentaje_produccion`, o regla de plan vigente cuando corresponda). Solo Responsable modifica esa tasa y se guarda snapshot de liquidación. No mezclar con cobro del Responsable.
- **Pago del Usuario a Gestores**: producción ingresada por cada Gestor × porcentaje de comisión asignado a ese Gestor conforme a la regla actual, manteniendo la autorización de edición vigente hasta revisión expresa.
- **Separación contable**: el Responsable **cobra** al Usuario con 3 %/3,5 % y, por otro movimiento independiente, **paga** al Usuario según porcentaje asignado. Nunca efectuar compensación automática.
- **Cobrado**: SUMA de abonos confirmados, nunca de comprobantes adjuntados sin validar.
- **Saldo por cobrar**: cobro devengado – cobrado; no negativo, excedentes requieren ajuste separado.
- **Pagado a Gestores**: suma de transferencias CONFIRMADAS a Gestores, no de programaciones.
- **Resultado de caja del Usuario** (referencial): cobros efectivamente ingresados al Usuario – pagos efectivamente efectuados al Responsable – pagos a Gestores – otros egresos registrados. No presentar `producción bruta - pagos` como efectivo remanente.

La palabra *cobrado* debe mostrar **quién cobró a quién**; evitar confusión entre dinero del cliente al Usuario y dinero del Usuario al Responsable. Conciliar con comprobantes separados.

## Estados del cobro
`PENDIENTE`: sin abonos confirmados. `PARCIAL`: uno o más abonos y saldo positivo. `PAGADO`: saldo cero y abonos confirmados. `POSTERGADO`: hay nueva fecha compromiso; no modifica el saldo devengado. `PROGRAMADO`: plan de pago registrado, sin transferencia aún. `EN_REVISION`: voucher adjunto esperando conciliación. `ANULADO`: reversión formal auditada, no borrar movimientos.

Cada prórroga registra fecha inicial, fecha nueva, motivo, autor y sello horario. Cada prorrateo registra cuotas (monto, vencimiento, moneda, estado), suma exacta = saldo al momento de generar plan. Abonos parciales consumen cuotas y saldo transaccionalmente.

## Modelo incremental propuesto (migración 0015 o siguiente libre)
1. `cobros_usuarios`: UUID id/tenant/responsable/usuario, inicio/fin, moneda, produccion_bruta, porcentaje_snapshot, monto_devengado, monto_pagado, saldo, estado, timestamps, revision. Unicidad tenant+usuario+período+moneda con control de solapamientos.
2. `cuotas_cobro_usuario`: UUID, cobro_id, número de cuota, fecha_compromiso, importe, saldo, estado, observación.
3. `abonos_cobro_usuario`: UUID, cobro_id, cuota_id opcional, fecha_operación, monto, referencia bancaria, estado conciliación, realizado_por, creado_at, idempotency_key.
4. `evidencias_abono_usuario`: UUID, abono_id, nombre, MIME permitido, ruta_storage protegida, SHA256, tamaño, fecha, cargado_por. Guardar archivo en almacenamiento privado y servir mediante autorización, no URL pública.
5. `historial_cobro_usuario`: entidad, acción, estado anterior/nuevo, actor, rol, timestamp, motivo, detalles JSON (sin datos bancarios sensibles ni rutas públicas).
6. `tasas_usuario_historial`: usuario_id, tasa de PAGO al Usuario, vigencia_desde/hasta, asignada_por (Responsable), timestamp. Evitar cambios retroactivos.\n7. `detalle_cobro_usuario`: cobro_id, expediente_id, receptor_id, snapshot de condición agente_retencion, tasa 3.00/3.50, base y comisión. Unicidad cobro_id+expediente_id; conservar trazabilidad por factura.

Todos los IDs deben verificarse con tenant + vínculo Responsable–Usuario; el identificador pasado por el navegador nunca da acceso por sí mismo.

## API propuesta
- `GET /api/v1/usuario/contabilidad?mes=YYYY-MM&moneda=PEN`: solo Usuario autenticado, resumen + series mensuales + detalle de sus Gestores.
- `GET /api/v1/usuario/cobros`: tasa vigente en solo lectura, liquidaciones y calendario de pagos al Responsable.
- `GET /api/v1/responsable/cobros-usuarios?usuario_id=...&mes=...`: solo Responsable propietario.
- `PATCH /api/v1/responsable/usuarios/{id}/porcentaje`: porcentaje de PAGO al Usuario, solo Responsable del Usuario; rango 0..100, Decimal y auditoría; nunca confiar en rol declarado por cliente.
- `POST /api/v1/responsable/cobros-usuarios/cerrar-mes`: operación idempotente, snapshot de base/tasa y exclusión de períodos duplicados.
- `POST /api/v1/responsable/cobros-usuarios/{id}/cuotas`: programar o prorrogar con motivo y validación de sumas.
- `POST /api/v1/responsable/cobros-usuarios/{id}/abonos`: registrar abono pendiente de conciliación; confirmación explícita autorizada, no asumir dinero recibido.
- `POST /api/v1/responsable/cobros-usuarios/abonos/{id}/evidencia`: multipart, MIME JPG/PNG/PDF, análisis de tamaño, SHA256; nunca ejecutar archivos.
- `POST /api/v1/responsable/cobros-usuarios/abonos/{id}/confirmar`: idempotente; transacción con bloqueo de fila para actualizar saldos y estados.

## Navegación
**USUARIO**: `Cobros` (obligación calculada con tasas 3 % agente de retención / 3,5 % no agente, solo lectura), `Pago de Gestores` (obligaciones propias), `Contabilidad` (mes, año, moneda, producción, cobrado a clientes, pagado al Responsable, pagado a Gestores, saldos y resultado). Tabla con estados, próximos vencimientos, botón para visualizar vouchers autorizados, exportar reporte.

**RESPONSABLE**: `Mis Usuarios` incorpora exclusivamente la tasa editable del PAGO a Usuarios y fecha de vigencia; nueva sección `Cobros a Usuarios` con liquidación mensual, cuotas, vencimientos, vouchers y confirmaciones. Conservar `Cobros y clientes` existente: es distinto porque allí se exhibe producción por receptor. Conservar `Pago de Usuarios` como liquidación de pagos a favor de Usuario hasta clarificar su efecto económico; jamás compensar automáticamente cobros y pagos entre las partes.

## Matriz estricta de permisos financieros
| Rol | Cobros | Pagos | Comisiones y producción |
| --- | --- | --- | --- |
| SUPERADMIN / ADMINISTRADOR | Supervisión auditada según permisos | Supervisión auditada | Consulta según ámbito |
| RESPONSABLE | Cobros a sus Usuarios: 3 % / 3,5 % por facturas | Pagos a sus Usuarios con tasa configurada | Producción de Gestores de sus Usuarios |
| USUARIO | Consulta de los cobros que le registra Responsable | Pago a sus Gestores | Su producción y contabilidad mensual |
| GERENTE | **Sin sección ni endpoint de Cobros** | **Solo Pagos**, dentro de su ámbito | Consulta según permisos de negocio |
| SECRETARIA | **Sin Cobros** | **Sin Pagos** | Solo operaciones documentales autorizadas |
| GESTOR | Sin Cobros | Sin Pagos | Solo sus registros de producción |

No basta con ocultar el menú: validar autorización en cada endpoint y en consultas por tenant, rol y responsable. En el menú actual de Gerente hay `/pagos` y no `/mi-equipo/cobros`; Secretaría ya no tiene menú financiero. Revisar que las APIs y otros accesos directos cumplan exactamente esta matriz.

## Pruebas obligatorias antes del VPS
- Responsable A no puede consultar ni modificar Usuario de Responsable B, incluso si conoce UUID.
- Usuario no puede editar porcentaje ni confirmar abonos.
- Cambio de tasa de PAGO al Usuario no altera períodos cerrados.\n- Facturas de agente de retención usan exactamente 3 %; facturas no agentes exactamente 3,5 %, aunque ambas pertenezcan al mismo Gestor/Usuario.\n- La suma base incluye TODOS los expedientes ingresados por Gestores sin duplicados, independientemente de su cobro.\n- Gerente solo puede acceder a Pagos; Secretaría tiene 403 para Cobros y Pagos por acceso directo a API.
- Misma factura cargada varias veces cuenta una sola vez.
- Separación PEN y USD, sin sumar monedas.
- Dos solicitudes simultáneas de abono con misma idempotency_key acreditan una sola vez.
- Abono parcial → saldo exacto; prórroga y cuotas conservan saldo; abono excesivo rechaza.
- Voucher pendiente NO implica `PAGADO`; guardar/descargar restringido al tenant y rol.
- Mes sin movimientos da ceros y muestra estado apropiado.
- Migración `alembic upgrade head`, pruebas pytest, frontend typecheck/build y smoke tests RBAC.

## Verificaciones del código actual (09/10/2026)
- `frontend/src/App.tsx` presenta `/pago-gestores` a Usuario, pero carece de Cobros y Contabilidad de Usuario.
- `backend/app/api/routes/pagos_gestores.py` programa pagos de Gestores y calcula la tasa del Gestor sobre sus expedientes.
- `backend/app/models.py` contiene `Miembro.porcentaje_produccion` y `Gestor.porcentaje_comision`.
- `frontend/src/paginas/MiEquipoResponsable.tsx` ofrece los paneles Responsable de producción de clientes y pago a Usuarios, que no sustituyen el nuevo cobro de Responsable a Usuario.
- `backend/app/api/deps.py` limita explícitamente los endpoints del rol Responsable: habrá que ampliar su lista de acceso y probarla.

**Pendiente:** implementación backend/frontend, migración, validación CI, despliegue staging y recién después producción VPS con respaldo y rollback probado.
