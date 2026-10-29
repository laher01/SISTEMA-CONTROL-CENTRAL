# S.P.T. — logística de operaciones pesqueras

**S.P.T. (Sistema Pesquero de Trazabilidad)** es la plataforma. Cada organización opera como
tenant independiente; **SNIDERFISH es el tenant piloto y plantilla**, no el nombre ni el dueño de
la plataforma.

El módulo `/api/v1/pesca` registra la operación desde el reporte del armador hasta la recepción
en planta. Los datos se aíslan por `tenant_id`; los pesos se guardan con su fuente y no se mezclan.

## Secuencia de operación

1. **Reporte y preparación:** se crea una operación con armador reportante, puerto, muelle, planta,
   comprador, remitente, destinatario, facturador, toneladas declaradas, precio propuesto, horarios
   previstos y responsables (jefe de bahía, encargado de muelle y apuntador). Los datos de una
   operación no modifican la plantilla del tenant.
2. **Confirmación comercial:** el comprador registrado confirma el precio por tonelada. La primera
   confirmación queda fechada, ligada al usuario que la ingresó y bloqueada para cambios normales.
   Una corrección requiere un flujo separado y auditado; no se sobrescribe el precio confirmado.
3. **Control documental antes de descargar:** se deben adjuntar matrícula, permiso de pesca,
   certificado SANIPES, constancia/reporte satelital, visto bueno de PRODUCE y Guía de Remisión
   Remitente. `POST /operaciones/{id}/iniciar-descarga` rechaza el inicio mientras falte el precio
   confirmado o cualquiera de esos documentos.
4. **Descarga en muelle:** se vinculan embarcación, armador y patrón por separado, se registra el
   peso declarado por embarcación y los pesos/cajas descargados por vehículo. Los registros de
   inicio y fin de descarga son distintos de los horarios previstos.
5. **Despacho y recepción:** antes de salir del muelle, cada vehículo debe tener carga asignada,
   Guía Remitente, Guía Transportista, acta de fiscalización y formato de descarga adjuntos. Se
   registra la hora real de salida. En planta se registran llegada, inicio y fin de descarga,
   peso aceptado, unidad, rechazo y evidencia de pesaje.
   Los valores se normalizan a kg para comparar.
6. **Cierre documental:** se cargan formato de descarga, acta de fiscalización, guía de transporte,
   peso de planta y certificado de procedencia, entre otros. Una misma evidencia puede vincularse a
   varios vehículos. El historial conserva actor, momento y acción.
7. **Gastos y conciliación:** cada movimiento de operación identifica pagador, beneficiario,
   concepto, monto/moneda, cantidad y tarifa opcionales. Se distinguen gastos pagados por la
   empresa, gastos operativos pagados por el jefe de bahía que esperan reembolso y adelantos de la
   empresa al armador. Se pueden adjuntar comprobantes y registrar reembolsos o devoluciones
   parciales; el saldo se calcula sin superar el monto original.
8. **Préstamos personales:** el préstamo de dinero propio del jefe de bahía se registra sin
   `operacion_id`, con constancia opcional, abonos parciales y saldo. El listado solo devuelve al actor que lo registró.
   No aparece en los gastos, pesos ni movimientos de la operación y nunca se descuenta de la pesca.
9. **Factura y presentación a pago:** después de cerrar la recepción y adjuntar el certificado de
   procedencia, Secretaría registra serie/correlativo y carga el comprobante. El sistema marca el
   expediente como `lista_para_pago`; no emite la factura ni confirma el pago.

## Rutas principales

- `POST/GET /api/v1/pesca/operaciones`
- `POST /api/v1/pesca/operaciones/{id}/confirmar-precio`
- `POST /api/v1/pesca/operaciones/{id}/factura`
- `POST /api/v1/pesca/operaciones/{id}/iniciar-descarga`
- `POST /api/v1/pesca/operaciones/{id}/embarcaciones`
- `POST /api/v1/pesca/operaciones/{id}/vehiculos`
- `POST /api/v1/pesca/vehiculos/{id}/cargas`
- `POST /api/v1/pesca/vehiculos/{id}/traslado/iniciar`
- `POST /api/v1/pesca/vehiculos/{id}/planta/iniciar` y `/planta`
- `POST /api/v1/pesca/operaciones/{id}/documentos`
- `GET /api/v1/pesca/operaciones/{id}/documentacion`, `/resumen`, `/historial` y `/movimientos`
- `POST /api/v1/pesca/movimientos` y `POST /movimientos/{id}/abonos`
- `GET /api/v1/pesca/movimientos-personales`

## Pesos que permanecen separados

- **Declarado:** estimación que reporta la embarcación.
- **Muelle:** peso que queda asignado al vehículo durante la descarga.
- **Planta:** peso aceptado por la planta, respaldado por evidencia.

No se usa ninguno para reemplazar los otros. La liquidación, diferencias autorizadas, excedentes,
descuentos y pérdida de deudas quedan pendientes de reglas aprobadas; este módulo registra hechos y
saldos de movimientos, no decide esos cálculos comerciales.

## Límites antes de habilitar a usuarios finales

El entorno actual usa Cloudflare Access como barrera externa; `X-Actor` solo existe para desarrollo
local y no autentica a nadie. Aún falta implementar permisos por rol para Superadmin S.P.T.,
administrador del tenant, jefe de bahía, encargado, apuntador y armador/patrón. No se deben exponer
estas rutas a usuarios finales hasta integrar y verificar ese control. El envío/facturación y el
cobro de facturas permanecen fuera del módulo operativo.
