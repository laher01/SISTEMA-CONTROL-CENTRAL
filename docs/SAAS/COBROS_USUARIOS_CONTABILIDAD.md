# Motor financiero jerárquico — especificación corregida 09/10/2026

**Estado: diseño en rama, no desplegado.** Sustituye íntegramente el planteamiento anterior que confundía cobros del Responsable al Usuario.

## Cadena económica y límites de información

1. GERENTE **paga al RESPONSABLE**, quien **cobra de Gerencia**. El cálculo vigente se encuentra en `backend/app/api/routes/pagos_responsables.py` y usa 3 % si el receptor es agente de retención y 3,5 % en otro caso, salvo las reglas personalizadas existentes aprobadas. Reutilizar `PagoResponsableERP` y nunca crear cobro duplicado.
2. RESPONSABLE **paga al USUARIO** por el porcentaje que el Responsable define sobre la producción introducida por los Gestores de ese Usuario. Reutilizar `PagoERP` y `Miembro.porcentaje_produccion` / planes vigentes. Solo el Responsable puede fijar/modificar el porcentaje de su Usuario.
3. USUARIO **paga a GESTORES u otros beneficiarios** que autorice en su dominio, con porcentajes configurados por el propio Usuario cuando liquida. Los porcentajes se aplican sobre el total de producción que corresponda a cada liquidación/beneficiario. Puede incluir varias personas en una misma liquidación, incluso quien no sea Gestor, con concepto, identificación y sustento verificable.
4. GESTOR **solo conoce sus expedientes, su producción atribuida, el porcentaje propio, cuánto cobrará, sus depósitos y saldos**. No ve porcentajes ni importes de Usuario, Responsable o Gerencia, ni pagos a otros Gestores.

**Privacidad estricta:** USUARIO no sabe cuánto cobra el Responsable de Gerencia; GESTOR no sabe cuánto cobra Usuario del Responsable ni Responsable de Gerencia. No mostrar datos por frontend, API, exportaciones, reportes, chat automático, eventos, respuestas de error, auditores sin acceso o descarga de vouchers. Autorización RBAC con scope por tenant y propietario; pruebas directas por endpoint y UUID ajeno.

## Navegación definitiva por rol

| Rol | Cobros | Pagos | Vista de comisiones |
| --- | --- | --- | --- |
| GERENTE | Sin apartado Cobros | Pagos a Responsables | Solo datos necesarios de sus pagos |
| RESPONSABLE | Cobros recibidos de Gerencia (sus propios pagos) | Pagos a Usuarios propios | Producción de Usuarios/Gestores de su equipo; no pagos privados de Usuario a terceros |
| USUARIO | Solo cobros recibidos del Responsable (ingreso a favor suyo); sin conocer ingresos del Responsable | Liquidación múltiple a Gestores y otros beneficiarios | Solo sus márgenes, pagos y producción |
| GESTOR | Su saldo a cobrar | Sin pagos ajenos | Solo su liquidación individual |
| SECRETARIA | Ninguno | Ninguno | Solo control documental |
| ADMINISTRADOR/SUPERADMIN | Supervisión excepcional auditada, limitada al tenant | Supervisión auditada | Permisos explícitos |

Eliminar la sugerencia de pestaña «Cobros del Responsable al Usuario»: es conceptualmente incorrecta. Para Gerencia el menú será «Pagos», Responsable «Mis cobros» (solo dinero que Gerencia le debe o ha pagado) + «Pago a Usuarios», Usuario «Mis ingresos» + «Liquidar y pagar» + «Contabilidad», Gestor «Mi liquidación».

## Base de producción

Todas las facturas/expedientes distintos ingresados por los Gestores, atribuidos por `Expediente.gestor_id` y `Expediente.usuario_id`, forman la base de comisiones, independientemente de si se han cobrado. Excluir documentos anulados o eliminados y evitar contabilizar re-subidas del mismo comprobante; **no** usar pedidos previstos como ingreso.

La clasificación agente de retención procede de `Empresa.agente_retencion`, con control histórico cuando se cierre una liquidación. El cálculo en `pagos_responsables.py` ya contiene las reglas por cliente y los valores predeterminados 3 / 3,5 %: conservar compatibilidad y evitar una segunda fuente de verdad.

### Liquidación múltiple del Usuario

- Cabecera de período, moneda, alcance, producción total, total de comisiones asignadas, saldo aún no distribuido, estado y Usuario propietario.
- Partidas: beneficiario tipo `GESTOR` o `EXTERNO`, nombre/identificador, Gestor relacionado opcional, base de cálculo documentada, porcentaje individual, comisión = base × porcentaje / 100, cantidad a pagar, saldo, motivo del pago.
- Si el beneficiario es Gestor, por defecto la base es la producción de ese Gestor dentro del período, con posibilidad de seleccionar un conjunto verificable de facturas/expedientes, sin doble asignación cuando el modelo económico lo requiera. Para otros beneficiarios el Usuario selecciona la base atribuible y justifica la naturaleza del servicio; no atribuir documentos arbitrariamente a un tercero.
- La suma de partidas debe respetar el monto de la comisión/disponibilidad del Usuario cuando haya una referencia económica confirmada; no crear un «saldo ganado» artificial a partir de facturas no cobradas. Si el Usuario acuerda pagos superiores a su ingreso, registrar obligación y advertencia expresa sin ocultar el saldo negativo.
- Permitir 2, 3, 10 o más destinatarios; validación previa de monto, porcentaje, moneda, período y saldo, y vista previa antes de programar.
- Cada partida puede estar `PROGRAMADO`, `PENDIENTE`, `POSTERGADO`, `PARCIAL`, `EN_REVISION` o `PAGADO`. Separar el compromiso de pago de un depósito real.
- Abonos múltiples con fecha, cuota, monto, referencia, voucher privado, carga JPG/PNG/PDF, conciliación explícita, vencimientos y prórrogas; nunca marcar pagado solo por subir voucher.
- Historial inmutable de cambios, tasas y confirmaciones. No borrar pagos confirmados; utilizar reversión auditada.

## Modelo y API por implementar

Nuevas tablas propuestas `liquidaciones_usuario`, `liquidaciones_usuario_destinatarios`, `liquidaciones_usuario_abonos`, `liquidaciones_usuario_archivos` y `liquidaciones_usuario_eventos`, con claves UUID, `tenant_id`, `usuario_id`, restricciones de unicidad, índices por tenant y propietario, y snapshot de base/tasa por partida.

- `GET /api/v1/usuario/liquidaciones`: solo propias, sin datos de niveles superiores.
- `POST /api/v1/usuario/liquidaciones/cotizar`: partidas, porcentajes, bases, sumas, advertencias, sin escritura.
- `POST /api/v1/usuario/liquidaciones`: crear en una transacción, con clave de idempotencia.
- `POST /api/v1/usuario/liquidaciones/{id}/abonos`: registrar abono a partida y evidencia.
- `POST /api/v1/usuario/liquidaciones/{id}/conciliar`: confirmar conciliación de sus propias salidas con reglas de autorización.
- `GET /api/v1/gestor/mi-liquidacion`: solo partidas dirigidas al Gestor autenticado, exclusivamente campos de su propia comisión y pagos.
- `GET /api/v1/usuario/contabilidad`: ingresos de su Responsable (sin tasa ni producción del Responsable), obligaciones con Gestores/externos, total recibido/pagado/saldo y producción de sus Gestores.

## Cambios de permisos obligatorios

El rol GERENTE puede acceder a las rutas de `pagos_responsables` que le corresponden; **nunca** a un módulo genérico de cobros. El rol SECRETARIA no tendrá ni Cobros ni Pagos. En `pagos_responsables.py` solo GERENTE confirma un pago a Responsable. Los pagos de Responsable a Usuario se autorizan en `responsable.py`. Nunca retornar la comisión de Gerencia a Usuario ni Gestor.

## Inspección del código del repositorio

- `backend/app/api/routes/pagos_responsables.py` ya implementa el flujo Gerencia → Responsable (predeterminadas 3 y 3,5 %), reglas personalizadas y conciliación.
- `backend/app/api/routes/responsable.py` ya programa y confirma flujo Responsable → Usuario con porcentaje de Usuario.
- `backend/app/api/routes/pagos_gestores.py` solo maneja un Gestor por programación. Debe evolucionar a distribución múltiple y beneficiarios externos sin romper liquidaciones históricas.
- `frontend/src/paginas/PagoGestores.tsx` requiere formulario de múltiples destinatarios; `frontend/src/App.tsx` debe ocultar opciones no autorizadas.
- La seguridad necesita pruebas de acceso directo a API, porque ocultar menú no basta.

## Pruebas y despliegue

Pruebas de aislamiento cruzado Responsable / Usuario / Gestor, auditoría de comisiones ocultas en respuestas y exportaciones, duplicados, moneda, tasas, suma de partidas, redondeo, abonos parciales, cuotas/prórrogas, concurrencia, tenant ajeno, factura duplicada, migración y rollback.

Antes de subir a `main`: backend pytest + migración Alembic, frontend npm build, tests RBAC y verificación del workflow staging. El despliegue actual de `main` puede afectar una VPS existente; la Oracle usa configuración de destino distinta. No activar producción ni declarar éxito sin ejecución verificable y respaldo.
