# S.P.T. — logística de operaciones pesqueras

**S.P.T. (Sistema Pesquero de Trazabilidad)** es la plataforma. Cada organización opera como
tenant independiente; **SNIDERFISH es el tenant piloto y plantilla**, no el nombre ni el dueño de
la plataforma.

El módulo `/api/v1/pesca` registra la operación desde el reporte del armador hasta la recepción
en planta. Los datos se aíslan por `tenant_id`; los pesos se guardan con su fuente y no se mezclan.

## Secuencia de operación

1. **Reporte y preparación:** se crea una operación con armador reportante, puerto, muelle, planta,
   comprador, remitente, destinatario, facturador, toneladas declaradas, precio acordado ingresado por la embarcación, horarios
   previstos y responsables (jefe de bahía, encargado de muelle y apuntador). El Jefe de Bahía
   selecciona la cuenta específica del Apuntador de Muelle o Encargado de Muelle que anotará el pesaje. Los datos de una
   operación no modifican la plantilla del tenant.
2. **Acuerdo y confirmación del precio:** Patrón o Armador coordina por llamada el precio con el
   Jefe de Bahía o Gerente, lo ingresa en la operación y confirma que corresponde a ese acuerdo.
   Después, el Jefe de Bahía o Gerente acepta en el sistema ese mismo monto; no vuelve a digitarlo ni
   puede sustituirlo en ese paso. Ambas confirmaciones quedan auditadas. Solo Jefe de Bahía y Gerente
   consultan los montos; el Administrador del tenant no participa. Si aún está en preparación, el
   Patrón/Armador puede solicitar un ajuste con motivo y confirmar el nuevo monto; el precio vigente
   solo cambia cuando Jefe de Bahía o Gerente acepta ese mismo importe. Las dos versiones quedan en
   el historial.
3. **Control documental antes de descargar:** se deben adjuntar y dejar en estado verificado matrícula, permiso de pesca,
   certificado SANIPES, constancia/reporte satelital, visto bueno de PRODUCE y Guía de Remisión
   Remitente. `POST /operaciones/{id}/iniciar-descarga` rechaza el inicio mientras falte el precio
   confirmado o cualquiera de esos documentos. Un archivo pendiente u observado no habilita la descarga.
4. **Descarga en muelle:** se vinculan embarcación, armador y patrón por separado, se registra el
   peso declarado por embarcación y los pesos/cajas descargados por vehículo. El resumen acumula el
   peso y las cajas por vehículo y presenta el total apuntado por embarcación. Los registros de
   inicio y fin de descarga son distintos de los horarios previstos. El traslado guarda la salida
   del muelle, la llegada real a planta, el inicio de descarga en planta y su fin como cuatro hitos
   separados. Matrícula, embarcación,
   armador y patrón quedan copiados en la operación para que cambios posteriores en la ficha de la
   nave no alteren operaciones históricas. La lista de naves se cierra al autorizar la descarga.
5. **Trabajo de cuadrilla:** el Jefe de Cuadrilla es el único actor de cuadrilla con acceso al sistema.
   Registra por nombre a Lavadores, Cajeadores y Estibadores, y él mismo registra el control de sus
   labores por vehículo. No se crean cuentas para esos integrantes. La forma de pago puede ser única
   al Jefe de Cuadrilla o desglosada entre Lavador, Cajeador y Estibador; en ambos casos la entrega
   es en efectivo por medio del Jefe de Cuadrilla. En pago único se guarda el monto total; en
   desglose se exige un monto en efectivo para cada integrante activo registrado.
6. **Despacho y recepción:** antes de salir del muelle, cada vehículo debe tener carga asignada,
   Guía Remitente, Guía Transportista, acta de fiscalización y formato de descarga adjuntos y verificados. Se
   registra la hora real de salida. En planta se registran llegada, inicio y fin de descarga,
   peso aceptado, unidad, rechazo y evidencia de pesaje.
   Los valores se normalizan a kg para comparar.
7. **Expediente documental por etapa:** cada archivo se clasifica como Embarcación, Muelle y descarga,
   Traslado, Planta, Tramitadora, Facturación o General, y se vincula con la operación y, cuando aplica,
   con embarcaciones y vehículos. El Jefe de Bahía revisa los documentos operativos: deja cada archivo
   como pendiente, verificado u observado; observar exige motivo. Una observación bloquea la etapa que
   requiere ese documento. La carga de una corrección crea una nueva versión y conserva la anterior;
   la versión reemplazada deja de contar para los requisitos. El certificado de procedencia debe estar
   verificado antes de registrar la factura; el expediente de factura queda listo para presentar a pago
   solo cuando se verifica también el archivo de la factura. El historial conserva carga, versión,
   revisión, actor y momento. S.P.T. almacena los archivos emitidos por las partes o autoridades; no
   los declara emitidos oficialmente por la plataforma.
8. **Gastos y conciliación:** cada movimiento de operación identifica pagador, beneficiario,
   concepto, monto/moneda, cantidad y tarifa opcionales. Los gastos exigen categoría y CPE:
   muelle, hielo y flete requieren factura; cuadrilla y apuntador, RHE; solo se admite boleta de
   muelle si se explica que no puede emitir factura. Cada gasto requiere adjuntar tanto el CPE
   como la evidencia del pago. Los reembolsos y devoluciones parciales requieren un voucher por
   cada abono, se registran con fecha y actor autenticados, y no pueden superar el monto original.
9. **Préstamos personales:** el préstamo de dinero propio del jefe de bahía se registra sin
   `operacion_id`, con constancia opcional, abonos parciales y saldo. El listado solo devuelve al actor que lo registró.
   No aparece en los gastos, pesos ni movimientos de la operación y nunca se descuenta de la pesca.
10. **Factura y presentación a pago:** después de cerrar la recepción y adjuntar el certificado de
   procedencia, Secretaría registra serie/correlativo y carga el comprobante. El sistema marca el
   expediente como `lista_para_pago`; no emite la factura ni confirma el pago. Si se reintenta subir
   el mismo archivo a la misma operación, el sistema reutiliza el documento y evita duplicarlo.

## Rutas principales

- `POST/GET /api/v1/pesca/operaciones`
- `POST /api/v1/pesca/operaciones/{id}/confirmar-acuerdo-embarcacion` confirma el monto digitado por Patrón/Armador
- `POST /api/v1/pesca/operaciones/{id}/confirmar-precio`
- `POST /api/v1/pesca/operaciones/{id}/solicitar-ajuste-precio` y `/aceptar-ajuste-precio`
- `PUT /api/v1/pesca/operaciones/{id}/responsable-pesaje-muelle` designa al apuntador responsable (Jefe de Bahía)
- `GET /api/v1/pesca/operaciones/{id}/responsables-pesaje-muelle/candidatos` lista las cuentas que Jefe de Bahía puede designar
- `PUT /api/v1/pesca/operaciones/{id}/cuadrilla/pago` configura pago único o desglose (Jefe de Cuadrilla)
- `POST /api/v1/pesca/operaciones/{id}/factura`
- `POST /api/v1/pesca/operaciones/{id}/iniciar-descarga`
- `POST /api/v1/pesca/operaciones/{id}/embarcaciones`
- `POST /api/v1/pesca/operaciones/{id}/vehiculos`
- `POST /api/v1/pesca/vehiculos/{id}/cargas`
- `POST /api/v1/pesca/vehiculos/{id}/traslado/iniciar`
- `POST /api/v1/pesca/vehiculos/{id}/planta/iniciar` registra llegada; `/planta/descarga/iniciar` registra inicio de descarga y `/planta` registra el peso final
- `GET/PUT /api/v1/pesca/operaciones/{id}/cuadrilla` asigna integrantes por actividad
- `GET/PUT /api/v1/pesca/vehiculos/{id}/actividades` registra lavado, cajeo y estiba con sus revisiones
- `POST /api/v1/pesca/operaciones/{id}/documentos`
- `PUT /api/v1/pesca/documentos/{id}/revision` (Jefe de Bahía; verifica u observa con motivo)
- `GET /api/v1/pesca/operaciones/{id}/documentacion`, `/resumen`, `/historial` y `/movimientos`
- `POST /api/v1/pesca/movimientos`, `/movimientos/{id}/comprobante`, `/movimientos/{id}/voucher`
  y `/movimientos/{id}/abonos` (el abono operativo exige voucher en el mismo envío)
- `GET /api/v1/pesca/movimientos-personales`

## Pesos que permanecen separados

- **Declarado:** estimación que reporta la embarcación.
- **Muelle:** peso que queda asignado al vehículo durante la descarga.
- **Planta:** peso aceptado por la planta, respaldado por evidencia.

No se usa ninguno para reemplazar los otros. La liquidación, diferencias autorizadas, excedentes,
descuentos y pérdida de deudas quedan pendientes de reglas aprobadas; este módulo registra hechos y
saldos de movimientos, no decide esos cálculos comerciales.

## Control de acceso y límites

Todas las rutas requieren una sesión válida de la plataforma y usan el tenant de esa sesión. El
actor del historial y de los movimientos se toma de la identidad autenticada, no de un encabezado
editable por el cliente. Los actores S.P.T. son asignaciones de función propias del módulo y se
administran por tenant; no reutilizan permisos de otros proyectos.

| Actor S.P.T. | Función implementada en esta logística |
| --- | --- |
| Administrador del tenant | Asigna y desactiva actores pesqueros. No confirma, consulta ni recibe permisos para decidir precios. |
| Jefe de Bahía | Confirma y consulta precios; coordina descarga, registra gastos y préstamos propios, y cierra la operación. |
| Gerente | Confirma y consulta precios. |
| Encargado de muelle | Prepara muelle y vehículos; puede pesar cajas en muelle si el Jefe de Bahía lo designa para esa operación. |
| Armador / Patrón | Reporta la operación, ingresa y confirma el precio que acordó con Jefe de Bahía o Gerente; puede solicitar un ajuste antes de iniciar la descarga. |
| Apuntador de muelle | Pesa cajas con pesca y anota pesos y totales por embarcación si el Jefe de Bahía lo designa para esa operación. |
| Apuntador de planta | Registra peso y evidencia recibidos en planta. |
| Jefe de cuadrilla | Único acceso digital de cuadrilla; registra nombres, controla labores y coordina el pago en efectivo. |
| Secretaría | Registra la factura y adjunta documentación. |
| Tramitadora | Adjunta documentación de operación. |
| Transportista | Se registra como chofer y vehículo; sus acciones digitales propias siguen pendientes de definir. |

SUPERADMIN S.P.T. conserva el control global de tenants; esta versión no le permite
entrar a la operación ni ver precios a través de las rutas de pesca. La emisión electrónica y
presentación/cobro de facturas requieren definir la integración externa y el actor que confirma el
pago. Las acciones digitales propias del Transportista y las reglas de liquidación (diferencias,
excedentes, descuentos y deudas) requieren especificación aprobada antes de automatizarlas.
