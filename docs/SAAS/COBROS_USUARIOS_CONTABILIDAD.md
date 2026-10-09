# Cobros del Responsable al Usuario y Contabilidad del Usuario

Estado: especificación técnica para implementación en rama de trabajo; **no desplegar sin pruebas**.

## Alcance y jerarquía
`RESPONSABLE -> USUARIO -> GESTOR`. La cartera solo se consulta o modifica dentro del mismo tenant. Cada Responsable administra porcentajes exclusivamente de Usuarios cuyo `responsable_id` sea su propio `miembro_id`. La cuenta Usuario solo lee su tasa y sus movimientos; Gestor no accede a esta contabilidad. Administración supervisa con permisos explícitos y auditoría. El porcentaje del Usuario (`Miembro.porcentaje_produccion`) NO es el porcentaje de comisión del Gestor (`Gestor.porcentaje_comision`).

La página `/pago-gestores` existente es una obligación del Usuario hacia sus Gestores, y no equivale a cobros del Responsable ni a ingresos recibidos.

## Base económica
Para cada Usuario, mes calendario y moneda:
- **Producción bruta**: SUMA de `Expediente.importe_total` donde `Expediente.usuario_id` es ese Usuario, `gestor_id` pertenece a Gestores vigentes/relacionados del Usuario, `deleted_at IS NULL`, y `fecha_emision` pertenece al período. Prohibido sumar de nuevo facturas re-subidas.
- **Tasa cobrada por Responsable**: `Miembro.porcentaje_produccion`, asignada por Responsable; guardar *snapshot* al cierre del mes para que cambios posteriores no modifiquen liquidaciones históricas.
- **Cobro devengado**: producción bruta × tasa / 100; usar Decimal y redondeo a 2 decimales según regla monetaria acordada.
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
6. `tasas_usuario_historial`: usuario_id, tasa, vigencia_desde/hasta, asignada_por (Responsable), timestamp. Evitar cambios retroactivos.

Todos los IDs deben verificarse con tenant + vínculo Responsable–Usuario; el identificador pasado por el navegador nunca da acceso por sí mismo.

## API propuesta
- `GET /api/v1/usuario/contabilidad?mes=YYYY-MM&moneda=PEN`: solo Usuario autenticado, resumen + series mensuales + detalle de sus Gestores.
- `GET /api/v1/usuario/cobros`: tasa vigente en solo lectura, liquidaciones y calendario de pagos al Responsable.
- `GET /api/v1/responsable/cobros-usuarios?usuario_id=...&mes=...`: solo Responsable propietario.
- `PATCH /api/v1/responsable/usuarios/{id}/porcentaje`: solo Responsable del Usuario; rango 0..100, Decimal y auditoría; nunca confiar en rol declarado por cliente.
- `POST /api/v1/responsable/cobros-usuarios/cerrar-mes`: operación idempotente, snapshot de base/tasa y exclusión de períodos duplicados.
- `POST /api/v1/responsable/cobros-usuarios/{id}/cuotas`: programar o prorrogar con motivo y validación de sumas.
- `POST /api/v1/responsable/cobros-usuarios/{id}/abonos`: registrar abono pendiente de conciliación; confirmación explícita autorizada, no asumir dinero recibido.
- `POST /api/v1/responsable/cobros-usuarios/abonos/{id}/evidencia`: multipart, MIME JPG/PNG/PDF, análisis de tamaño, SHA256; nunca ejecutar archivos.
- `POST /api/v1/responsable/cobros-usuarios/abonos/{id}/confirmar`: idempotente; transacción con bloqueo de fila para actualizar saldos y estados.

## Navegación
**USUARIO**: `Cobros` (lo que debe al Responsable, tasa solo lectura), `Pago de Gestores` (obligaciones propias), `Contabilidad` (mes, año, moneda, producción, cobrado a clientes, pagado al Responsable, pagado a Gestores, saldos y resultado). Tabla con estados, próximos vencimientos, botón para visualizar vouchers autorizados, exportar reporte.

**RESPONSABLE**: `Mis Usuarios` incorpora tasa editable y fecha de vigencia; nueva sección `Cobros a Usuarios` con liquidación mensual, cuotas, vencimientos, vouchers y confirmaciones. Conservar `Cobros y clientes` existente: es distinto porque allí se exhibe producción por receptor. Conservar `Pago de Usuarios` como liquidación de pagos a favor de Usuario hasta clarificar su efecto económico; jamás compensar automáticamente cobros y pagos entre las partes.

## Pruebas obligatorias antes del VPS
- Responsable A no puede consultar ni modificar Usuario de Responsable B, incluso si conoce UUID.
- Usuario no puede editar porcentaje ni confirmar abonos.
- Cambio de tasa no altera períodos cerrados.
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
