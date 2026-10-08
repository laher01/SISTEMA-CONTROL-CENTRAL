# Reforma: Responsables y liquidación jerárquica de producción

Estado: propuesta funcional documentada, **no implementada ni desplegada**. Fecha: 2026-10-08.

## 1. Estructura
Tenant > Administrador > Gerencia > Responsable > Usuario > Gestor. ADMINISTRADOR audita y ve todos los niveles; GERENTE solo ve Responsables y pagos al Responsable, sin listado de Usuarios/Gestores ni sus datos; RESPONSABLE solo ve sus Usuarios y sus pagos a Usuarios, no los Gestores internos; USUARIO solo ve sus Gestores y sus pagos a Gestores; GESTOR solo sus operaciones, sin pagos ajenos. Las API y exportaciones deben cumplir esta regla, no solo ocultar columnas en frontend. La Cuenta Acceso define un rol vigente y ámbito derivado del servidor.

El Responsable crea/invita sus Usuarios; el Usuario crea/invita sus Gestores. El Administrador puede corregir asignaciones con auditoría. Registrar created_by, parent_id, tenant_id, fecha inicio/fin de relación, y evitar reasignación retroactiva de documentos/pagos históricos. Desactivar no elimina historia.

## 2. Regla de titularidad y producción
Una factura pertenece a un único expediente comercial por tenant, y a una sola atribución operativa para un periodo. No duplicar si XML, PDF y voucher pertenecen al mismo comprobante. Producción por Gestor y por Usuario; Responsable totaliza Usuarios; gerencia totaliza Responsables. Documentos no validados, anulaciones, notas correctivas, diferencias monetarias y ajustes deben quedar explícitos bajo las reglas de negocio aprobadas. No mezclar PEN/USD ni omitir retenciones/adelantos.

Responsables iniciales citados: Luis Arévalo, Joel Peña, Joel Moscoso y Óscar Centeno. Tasa base declarada 3.5 % para cada uno, versionada con vigencias, periodos y base definida. Esta cifra es una regla contractual interna, no tributaria ni una deducción legal.

Usuarios a asociar inicialmente a Luis Arévalo (pendiente de verificación de identidades y vigencias):
WILLI01, LUIS01, JOSE01, MIGUEL01, LILI01, MAGO01, MARIO01, JAVIER01, JOSE-CHATA01, CARLO-PERUFROST01, ORESTES01, CARROHIELO01, CARROHIELO02.
CARROHIELO02 apareció dos veces en la solicitud: **no crear dos cuentas** sin confirmación.

## 3. Cálculo
ProduccionResponsable(periodo, moneda) = Σ produccionValida(usuario de su cartera en ese periodo, moneda).
BrutoResponsable = redondear(ProduccionResponsable × porcentaje vigente /100, 2).
NetoResponsable = BrutoResponsable - adelantos aplicables - descuentos/autorizaciones + ajustes explícitos.
En Usuarios y Gestores los planes son independientes. No descontar automáticamente comisiones de subniveles del pago del Responsable: la obligación dependerá del convenio. Regla única de redondeo, congelación de liquidaciones aprobadas, manejo de reversos, auditoría y comprobante de pago.

## 4. Pagos y visibilidad
Gerencia consulta lista de Responsables, montos agregados por periodo/moneda y paga al Responsable. Responsable consulta sus Usuarios y liquida sus planes; Usuario consulta sus Gestores y liquida planes individuales. Administración ve todo y aprueba o supervisa de acuerdo con las políticas. Separación de funciones: calculador, aprobador y pagador verificables en bitácora. Un mismo pago no puede ejecutarse dos veces ni asignarse a dos receptores.

## 5. Reglas especiales del Usuario JAVIER01 / Jonatan
El usuario indica que existe fórmula particular para Jonatan/Javier. **La definición cuantitativa exacta no se encontró confirmada en los materiales revisados**, por lo cual no debe inventarse. Diseñar motor declarativo, por version y alcance de Usuario, que admite tramos, tasas por cliente/proveedor, mínimos, topes, retenciones, ajustes o repartos solo después de aportar la fórmula autorizada. La excepción solo cambia la liquidación propia de JAVIER01 y no altera por defecto el 3.5% agregado del Responsable.

## 6. Estado existente y migración
La documentación actual dice ADMINISTRADOR -> GERENTE/SECRETARIA -> USUARIO -> GESTOR. El módulo backend/app/api/routes/pagos.py valida acceso de GERENTE y ADMINISTRADOR a lista de Usuarios y Gestores; esta exposición contraviene las nuevas reglas. Hay planes y pagos ligados a usuario_id y porcentaje de plan; NO reinterpretarlos como Responsable sin una migración de esquema y datos. Proponer tablas relacionales de Responsable y asignación Usuario-Responsable con vigencia; liquidaciones separadas por beneficiario y nivel, evitando cambios retroactivos. Mantener historial y resolver Usuarios sin Responsable asignado.

## 7. Pruebas obligatorias para entrega
- GERENTE no puede acceder por API ni exportación a lista de Usuarios/Gestores, aunque pase IDs manuales.
- Responsable A no ve Usuarios ni pagos de Responsable B; Usuario A no ve Gestores de Usuario B; Gestor no ve pagos.
- Sumatorias conciliadas con las facturas comerciales únicas y sus ajustes, para dos monedas.
- Alta por Responsable/Usuario con vínculo obligatorio y protección contra escalamiento de permisos.
- Reglas especiales versionadas; periodos cerrados inmutables; migración sin pérdida de pagos pasados.
- Reintentos de pagos idempotentes; logs de aprobación y recibos; backups/restauración.
- Documentar fórmula de JAVIER01 antes de habilitar cálculos especiales.

No desplegar en productivo hasta definir vigencia, usuarios definitivos, fórmula JAVIER01, compatibilidad histórica y pasar pruebas.
