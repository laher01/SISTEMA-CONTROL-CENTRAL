# Responsable: usuarios, tarifas, cobros, liquidaciones y contabilidad

Estado: especificación aprobable / implementación pendiente. Rama: `feature/responsable-tarifas-liquidaciones`.
Origen: requisitos del 09/10/2026, revisión de pantallas de VPS antigua y módulos existentes (`MiEquipoResponsable.tsx`, `Pagos.tsx`, `ComisionesResponsables`).

## 1. Invariantes económicas

- La producción representa exclusivamente operaciones reales respaldadas por expedientes únicos elegibles. No equivale a dinero cobrado.
- Los presupuestos de pedidos y las asignaciones no constituyen producción liquidable. No reutilizar montos de pedido como base adicional.
- Separar claramente: producción devengada; tarifa aplicable; comisión calculada; liquidación; programación; pago efectivamente confirmado; saldo.
- Cálculos con Decimal, moneda y redondeo a 2 decimales al consolidar cada componente de la liquidación; ninguna suma cruzará PEN y USD.
- No duplicar movimientos cuando se recalcula el mismo período o se adjunta/reprocesa un expediente. Las liquidaciones almacenan referencias a sus líneas de producción.
- Una rectificación de expediente previamente liquidado crea un ajuste trazable, nunca cambia silenciosamente un pago histórico.
- Periodos parcialmente solapados solo liquidan líneas elegibles aún no liquidadas. Se previenen dobles pagos mediante transacción y restricciones de unicidad.
- Programar un pago NO confirma desembolso. El voucher es soporte y debe conciliarse con el monto pagado; no sustituye confirmación.

## 2. Usuarios del Responsable

- Tabla: código/login, nombre, activo, número de clientes, porcentaje SIN agente de retención, porcentaje CON agente de retención, vigencia, acciones editar y restablecer clave.
- Al crear: nombre, ambas tasas, código único y contraseña temporal de un solo uso. Usuario puede ver sus tarifas pero no editarlas.
- Solo el Responsable propietario (o administradores con privilegio explícito y auditoría) puede editar las dos tarifas de sus usuarios. El backend verifica pertenencia, no se confía en el frontend.
- Tarifas versionadas por `effective_from/effective_to`; tasa snapshot en cada línea liquidada. Cambios retroactivos requieren flujo de ajuste aprobado.
- Contraseñas temporales generadas con CSPRNG, hash seguro, expiración, invalidación de sesiones cuando aplique, bandera de cambio obligatorio; contraseña nueva >= 8 caracteres. Nunca mostrar contraseña previa ni guardarla en texto plano; registrar evento de reset sin registrar el secreto.
- Las tasas se registran como porcentajes entre 0 y 100 con precisión definida. No habilitar porcentaje manual para saltarse el contrato vigente en la liquidación normal.

## 3. Clasificación de retención

- La categoría CON/SIN agente debe resolverse **por documento según estado aplicable a su fecha de emisión y operación tributaria**, no simplemente por una bandera actual del RUC.
- Conservar evidencia/origen de la clasificación y permitir revisión autorizada; si se desconoce la categoría, dejar la línea pendiente, sin asumir SIN.
- Separar condición tributaria de la existencia de una retención efectivamente aplicada, para no confundir categorías.
- Reglas particulares y vigencia legal requieren validación fiscal antes de producción.

## 4. Pago de Usuarios

Filtros: Usuario, fecha desde/hasta, moneda, cliente opcional, estado, categoría con/sin agente.

Detalle por cliente/RUC:
- expedientes únicos, cantidad de documentos elegibles y producción SIN/CON;
- tasas aplicadas según vigencia, importes por categoría y subtotal;
- ajustes auditados, saldo anterior, adelantos efectivamente pagados, pagos parciales, neto pendiente.

Fórmulas:
`comision_sin = sum(produccion_elegible_sin * tasa_sin / 100)`
`comision_con = sum(produccion_elegible_con * tasa_con / 100)`
`comision_total = comision_sin + comision_con + ajustes_aprobados`
`saldo_final = saldo_anterior + nuevo_devengado - pagos_confirmados - anticipos_aplicados`

- Saldo anterior proviene de libro de movimientos, NO de un nuevo asiento manual sumado a la producción ya liquidada.
- Migración inicial: asiento de apertura por usuario/moneda, corte de fecha, soporte, aprobación y clave única. Se prohíbe repetir apertura.
- Adelantos aplicados una sola vez mediante referencia única. Si exceden deuda, conservar crédito/anticipo a favor con saldo separado.
- El usuario puede recibir abonos parciales; historial inmutable de programación, postergación, abono, pago final, anulación y reversión.
- Capturar monto programado, fecha estimada, importe efectivamente pagado, fecha real, referencia, imagen/voucher privado, usuario que confirma y observación.
- Estados: PENDIENTE, PROGRAMADO, PARCIAL, POSTERGADO, PAGADO, ANULADO (transiciones verificadas).
- Pagos solo afectan caja cuando se confirman. Adjuntos con límites de tamaño/tipo, control de acceso, antimalware cuando esté disponible; URL no pública.

## 5. Cobros a clientes / gerencia

- Consolidado por cliente receptor y RUC, no filas repetidas por Usuario, con desglose expandible por Usuario.
- Cada cliente tiene tarifa vigente de cobro de Gerencia al Responsable, por moneda/contrato si corresponde; catálogo único autoritativo.
- Gerencia registra y aprueba cambios. Responsable solo propone; hasta aprobación y fecha de vigencia se aplica tarifa anterior.
- Una propuesta rechazada conserva versión, actor, fecha y motivo. Los cierres ya liquidados no se recalculan retroactivamente sin ajustes.
- Pantalla presenta producción, tarifa opcionalmente oculta con botón de ojo, importe a cobrar, cobrado, pendiente, adelantado y próximo vencimiento.
- Ocultar porcentajes es puramente visual: NO es autorización ni barrera de seguridad. El backend comprueba permisos.
- Gerencia programa pagos cada 10, 15, 30, 45 o 60 días (o fechas concretas) y registra pago parcial/postergación; Responsable ve los eventos en historial.
- No inferir cobro por la carga de un voucher: registrar y conciliar el hecho económico.

## 6. Contabilidad del Responsable

Por mes y moneda: saldo inicial + cobros efectivamente recibidos de Gerencia - pagos efectivamente hechos a Usuarios - otros egresos autorizados = saldo final de caja.
Mostrar por separado: derechos por cobrar, obligaciones por pagar, anticipos y programaciones; no mezclarlos con saldo de caja.
Consolidación por fecha de devengo Y por fecha de pago (dos vistas); alertar mora y conciliaciones pendientes.
Historial con filtros por periodo, estado, cliente, usuario, referencia; exportación CSV/PDF posteriormente.

## 7. Seguridad y auditoría

- Control de acceso estricto tenant -> gerencia -> responsable -> usuario -> gestor; nunca consultar recursos de otra cadena.
- Idempotency key en programación, confirmación y carga de voucher; integridad transaccional.
- Auditoría append-only: actor, tenant, entidad, valor antes/después, origen, fecha y motivo. Prohibido borrar pagos confirmados; usar reversión documentada.
- Las credenciales y evidencias de pago son datos confidenciales. No incluirlas en logs ni en respuestas amplias.

## 8. Contratos de backend sugeridos (no implementados todavía)

- `GET/POST /api/v1/miembros/mis-usuarios` (ampliar ambas tarifas);
- `PATCH /api/v1/miembros/mis-usuarios/{id}`;
- `POST /api/v1/miembros/mis-usuarios/{id}/reset-clave`;
- `GET /api/v1/responsable/pagos/desglose`;
- `POST /api/v1/responsable/pagos/cotizar` y `/programar` (reusar y versionar sin romper contratos);
- `GET /api/v1/responsable/cobros/clientes`;
- `POST /api/v1/responsable/cobros/tarifas/propuestas`;
- `POST /api/v1/gerencia/cobros/tarifas/propuestas/{id}/resolver`;
- `GET /api/v1/responsable/contabilidad`.
Diseñar migraciones, modelos, esquemas, RBAC y tests antes de exponer endpoints.

## 9. Secuencia segura de implementación

1. Inspeccionar modelos de datos, endpoints y pruebas existentes. Hacer backup de base y ensayar migración reversible.
2. Añadir tarifas duales versionadas y criterios de clasificación por documento; migrar tasas anteriores SIN inventar automáticamente tasa CON.
3. Editar usuarios y reset seguro de claves, con tests de permisos y expiración.
4. Crear libro de movimientos y proyecciones de producción desglosada, con tests de no doble conteo, solapes, ajustes y moneda.
5. Integrar cotización, programación, pagos parciales, saldos apertura, voucher y estados.
6. Integrar tarifas de clientes con propuestas y aprobación de Gerencia; vista por receptor.
7. Añadir contabilidad mensual y pruebas de conciliación; validar experiencia de usuario.
8. Ejecutar tests backend/frontend y CI, revisar pull request y desplegar por staging, no directo a VPS productiva.

## 10. Riesgos encontrados en implementación actual

- Alta de usuarios recibe un único `porcentaje_produccion`.
- Interfaz de Responsable expone `porcentaje_manual` en programación; revisar con contrato de tarifa dual.
- Pantalla de cobros agrupa registros por Usuario/receptor, en vez de resumen agregado por receptor.
- Contabilidad de caja del Responsable no aparece en el menú actual.
- Las capturas muestran un cálculo global con una tarifa única: no usar ese cálculo como prueba de deuda bajo la regla dual.

## Criterios de aceptación mínimos

- Dos usuarios con tarifas distintas y documentos mixtos calculan importes correctos sin duplicados.
- Cambiar tarifa hoy no altera un período ya liquidado.
- Cambio propuesto por Responsable no rige hasta aprobación de Gerencia.
- Pago parcial y postergación conservan saldo exacto y evidencia histórica.
- Un pago programado no reduce saldo de caja.
- Apertura inicial no se registra dos veces; anticipo no se descuenta dos veces.
- Usuario no puede editar tarifa, resetear otra cuenta ni acceder a voucher de otro equipo.
- Redondeo determinista, separación PEN/USD y pruebas de concurrencia de programación.

## 11. Aclaración de titularidad y devengo (09/10/2026)

- **Cobros del Responsable:** nacen de la producción elegible registrada por los Gestores de los Usuarios bajo ese Responsable, atribuida a cada cliente/receptor y multiplicada por la tarifa vigente de cobro aprobada por Gerencia. El importe por cobrar es visible aun si Gerencia no ha programado pagos. El Gerente únicamente programa/abona al Responsable y la ausencia de programación no oculta ni elimina el devengado. Distinguir producción cargada, producción validada y producción elegible; nunca considerar inválidos como cobrables.
- **Pagos a Usuarios:** únicamente el Responsable correspondiente programa, registra y confirma los pagos a todos sus Usuarios. La base individual suma la producción elegible de los Gestores vinculados al Usuario, desglosada por empresa y clasificación con/sin agente de retención; aplica las dos tarifas del Usuario fijadas por el Responsable. No confundir pago Responsable→Usuario con pago Gerencia→Responsable.
- **Saldos separados:** por cobrar a Gerencia = devengado a favor del Responsable + ajustes - cobros confirmados; por pagar a Usuarios = devengado de Usuarios + ajustes - pagos confirmados - anticipos imputados. Programaciones no alteran saldos de caja.
- **Pantalla Cobros y clientes:** mostrar total calculado por cobrar antes de toda programación, además de programado, recibido y pendiente. La aprobación de tarifa corresponde a Gerencia; la programación del cobro no aprueba ni crea devengo.
- **Pantalla Pago de Usuarios:** listar Usuarios, sus Gestores y clientes, producciones elegibles, categorías, comisiones, saldo anterior, pagos y adelantos; solo Responsable liquida sus Usuarios.
