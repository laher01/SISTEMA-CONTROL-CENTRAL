# 05_SUBSCRIPTION_ENGINE.md

# FACT CENTRAL SaaS

## SUBSCRIPTION ENGINE

Versión 1.0

---

# 1. Objetivo

Definir el motor oficial de suscripciones de FACT CENTRAL SaaS.

Este documento establece:

- cómo se crean los planes;
- cómo se asignan a los Tenants;
- cómo funciona la prueba gratuita;
- cómo se controlan límites y consumo;
- cómo se renueva una suscripción;
- cómo se aplica el periodo de gracia;
- cómo se suspende un Tenant;
- cómo se reactiva;
- cómo se cambia de plan;
- cómo se conserva el historial;
- cómo se auditan todos los cambios.

---

# 2. Principio fundamental

Toda organización dentro de FACT CENTRAL deberá estar asociada a:

- un Tenant;
- un plan;
- una suscripción;
- un periodo vigente;
- límites;
- consumo;
- estado de pago;
- estado operativo.

El uso del ERP dependerá de la combinación:

TENANT
+
PLAN
+
SUSCRIPCIÓN
+
ESTADO
+
CONSUMO
+
POLÍTICAS DE SEGURIDAD

---

# 3. Definiciones

## Plan

Conjunto de funcionalidades, límites y condiciones comerciales.

## Suscripción

Relación vigente entre un Tenant y un Plan durante un periodo.

## Periodo

Intervalo de tiempo facturable.

Ejemplos:

- mensual;
- trimestral;
- semestral;
- anual.

## Cuota

Límite de uso incluido en el Plan.

## Consumo

Uso real realizado por el Tenant.

## Exceso

Uso superior a la cuota contratada.

## Renovación

Creación o extensión de un nuevo periodo de suscripción.

---

# 4. Relación oficial

TENANT
↓
SUSCRIPCIÓN
↓
PLAN
↓
CUOTAS
↓
CONSUMO
↓
ESTADO OPERATIVO

Un Tenant podrá cambiar de Plan sin perder su identidad,
documentos, expedientes ni historial.

---

# 5. Estados de la Suscripción

Los estados oficiales serán:

## TRIAL

Prueba gratuita activa.

## ACTIVE

Suscripción pagada y operativa.

## PAYMENT_PENDING

Pago generado, aún no confirmado.

## GRACE_PERIOD

Periodo de gracia posterior al vencimiento.

## PAST_DUE

Pago vencido.

## SUSPENDED

Suscripción suspendida.

## CANCELLED

Renovación cancelada.

## EXPIRED

Periodo finalizado sin renovación.

## READ_ONLY

Acceso limitado a consulta.

## CLOSED

Suscripción cerrada definitivamente.

---

# 6. Estados del Tenant relacionados

El estado de la Suscripción afectará al estado del Tenant.

Ejemplo:

TRIAL
→ Tenant TRIAL_ACTIVE

ACTIVE
→ Tenant ACTIVE

GRACE_PERIOD
→ Tenant GRACE_PERIOD

SUSPENDED
→ Tenant SUSPENDED

READ_ONLY
→ Tenant READ_ONLY

CANCELLED
→ Tenant CANCELLED o ACTIVE hasta fin del periodo pagado

---

# 7. Planes oficiales iniciales

FACT CENTRAL podrá ofrecer planes como:

## PLAN PRUEBA

Para evaluación inicial.

## PLAN BÁSICO

Para operaciones pequeñas.

## PLAN EMPRESA

Para operaciones medianas.

## PLAN CORPORATIVO

Para alto volumen y funciones avanzadas.

## PLAN PERSONALIZADO

Configurado por Superadmin.

Los nombres comerciales podrán cambiar sin modificar la arquitectura.

---

# 8. Componentes de un Plan

Un Plan podrá definir:

- cantidad máxima de Usuarios;
- cantidad máxima de Gestores;
- cantidad máxima de Gerentes;
- cantidad máxima de Secretarías;
- cantidad máxima de Clientes;
- cantidad máxima de Proveedores;
- documentos procesados por mes;
- almacenamiento incluido;
- OCR incluido;
- procesamiento IA incluido;
- correos procesados;
- mensajes procesados;
- integraciones disponibles;
- cantidad de expedientes;
- exportaciones;
- retención histórica;
- soporte;
- prioridad de procesamiento;
- cantidad de nodos;
- frecuencia de backups;
- funcionalidades especiales;
- disponibilidad de API;
- uso de WhatsApp;
- uso de Gmail;
- uso de reportes avanzados;
- acceso a NEXUS;
- automatización avanzada;
- SLA.

---

# 9. Plan de Prueba

Todo Tenant nuevo podrá iniciar en:

TRIAL

La duración será configurable.

Ejemplo:

15 días.

La prueba podrá limitar:

- documentos;
- Usuarios;
- Gestores;
- almacenamiento;
- integraciones;
- IA;
- exportaciones;
- procesamiento mensual.

La prueba no deberá convertirse automáticamente en un Plan pagado
sin consentimiento y método de pago autorizado.

---

# 10. Inicio de la Prueba

Flujo:

REGISTRO DEL ADMINISTRADOR
↓
VERIFICACIÓN
↓
CREACIÓN DEL TENANT
↓
ASIGNACIÓN DE PLAN DE PRUEBA
↓
INICIO DEL PERIODO
↓
TRIAL_ACTIVE

El sistema registrará:

- fecha de inicio;
- fecha de vencimiento;
- días restantes;
- límites;
- consumo;
- funcionalidades habilitadas.

---

# 11. Fin de Prueba

Antes del vencimiento se enviarán avisos.

Ejemplo:

- 7 días antes;
- 3 días antes;
- 1 día antes;
- día de vencimiento.

Si el Administrador contrata:

TRIAL
→ ACTIVE

Si no contrata:

TRIAL
→ GRACE_PERIOD o READ_ONLY

según configuración.

---

# 12. Periodos de Suscripción

Los Planes podrán facturarse:

- mensual;
- trimestral;
- semestral;
- anual;
- personalizado.

Cada periodo tendrá:

- fecha de inicio;
- fecha de fin;
- fecha de vencimiento;
- moneda;
- importe;
- impuestos;
- descuentos;
- estado;
- referencia de pago.

---

# 13. Moneda

FACT CENTRAL deberá soportar múltiples monedas.

Ejemplos:

- PEN;
- USD;
- EUR.

Cada Suscripción tendrá una moneda principal.

La conversión, si existe, deberá registrar:

- tasa utilizada;
- fecha;
- origen de la tasa;
- importe original;
- importe convertido.

---

# 14. Renovación

La renovación podrá ser:

## Automática

Cuando exista un método de pago autorizado.

## Manual

Cuando el Administrador realice el pago mediante:

- transferencia;
- billetera;
- depósito;
- PayPal;
- otro medio.

La renovación deberá generar un nuevo periodo.

No se deberá reescribir el periodo anterior.

---

# 15. Renovación automática

Cuando esté habilitada:

FACT CENTRAL
↓
GENERA INTENTO DE COBRO
↓
PASARELA
↓
CONFIRMA O RECHAZA
↓
ACTUALIZA SUSCRIPCIÓN

Si el cobro se confirma:

ACTIVE

Si falla:

PAYMENT_PENDING o GRACE_PERIOD

---

# 16. Renovación manual

Flujo:

ADMINISTRADOR
↓
SELECCIONA PLAN
↓
GENERA ORDEN DE PAGO
↓
REALIZA PAGO
↓
ADJUNTA COMPROBANTE O PASARELA CONFIRMA
↓
VERIFICACIÓN
↓
ACTIVACIÓN DEL PERIODO

Los pagos manuales podrán requerir validación administrativa.

---

# 17. Métodos de pago

Los métodos podrán incluir:

- tarjeta de crédito;
- tarjeta de débito;
- transferencia bancaria;
- depósito;
- Yape;
- Plin;
- PayPal;
- Skrill;
- billeteras autorizadas;
- criptomonedas;
- pasarelas locales;
- pasarelas internacionales.

Cada integración será independiente del Motor de Suscripciones.

El Motor solamente utilizará estados normalizados.

---

# 18. Estados de pago

Los estados serán:

CREATED

PENDING

PROCESSING

CONFIRMED

FAILED

EXPIRED

CANCELLED

REFUNDED

PARTIALLY_REFUNDED

CHARGEBACK

UNDER_REVIEW

---

# 19. Cuotas

Cada Plan podrá contener cuotas.

Ejemplo:

PLAN EMPRESA

Usuarios: 20

Gestores: 100

Clientes: 200

Proveedores: 2,000

Documentos por mes: 50,000

Storage: 1 TB

OCR: 50,000 páginas

IA: 25,000 análisis

---

# 20. Consumo

FACT CENTRAL deberá registrar el consumo real del Tenant.

Ejemplos:

- Usuarios activos;
- Gestores activos;
- documentos recibidos;
- documentos procesados;
- páginas OCR;
- llamadas IA;
- almacenamiento utilizado;
- correos procesados;
- mensajes WhatsApp;
- exportaciones;
- llamadas API.

---

# 21. Medición del consumo

El consumo deberá registrarse por:

- Tenant;
- Plan;
- periodo;
- tipo de recurso;
- fecha;
- cantidad;
- origen;
- evento relacionado.

Ejemplo:

Tenant:
FC-A7K92M

Periodo:
2026-07

Recurso:
DOCUMENT_PROCESSING

Cantidad:
1

Documento:
DOC-123456

---

# 22. Contadores

El Motor podrá manejar:

- contadores acumulativos;
- contadores diarios;
- contadores mensuales;
- consumo de almacenamiento;
- consumo por módulo.

Los contadores deberán ser auditables.

---

# 23. Reinicio de cuotas

Las cuotas periódicas podrán reiniciarse al comenzar un nuevo periodo.

Ejemplo:

Documentos por mes.

No se reiniciarán automáticamente los recursos acumulativos.

Ejemplo:

Storage utilizado.

---

# 24. Límites suaves y límites duros

## Límite suave

Genera advertencia pero permite continuar.

## Límite duro

Bloquea nuevas operaciones.

Ejemplo:

80 %
→ Advertencia.

95 %
→ Alerta crítica.

100 %
→ Límite alcanzado.

110 %
→ Operación bloqueada o sobrecargo.

Los porcentajes serán configurables.

---

# 25. Alertas de consumo

FACT CENTRAL notificará cuando el Tenant alcance:

- 70 %;
- 80 %;
- 90 %;
- 100 %.

Ejemplo:

ALMACENAMIENTO UTILIZADO:
91 %

DOCUMENTOS PROCESADOS:
87 %

El Administrador podrá:

- cambiar de Plan;
- comprar capacidad adicional;
- limpiar datos temporales;
- exportar información;
- solicitar ampliación.

---

# 26. Exceso de consumo

Un Plan podrá definir:

## Bloqueo

No permite superar la cuota.

## Sobrecargo

Permite continuar y factura el exceso.

## Tolerancia

Permite un margen temporal.

## Escalado automático

Aumenta capacidad con aprobación.

La política deberá estar asociada al Plan.

---

# 27. Capacidad adicional

El Administrador podrá adquirir complementos.

Ejemplos:

- 100 GB adicionales;
- 10,000 documentos adicionales;
- 5 Usuarios adicionales;
- 25 Gestores adicionales;
- 10,000 páginas OCR;
- 5,000 análisis IA;
- integración WhatsApp;
- integración Gmail;
- API avanzada.

Los complementos tendrán:

- vigencia;
- precio;
- cantidad;
- estado;
- renovación.

---

# 28. Upgrade de Plan

El Administrador podrá subir de Plan.

Ejemplo:

BÁSICO
→ EMPRESA

El Upgrade podrá aplicarse:

- inmediatamente;
- al siguiente periodo;
- de forma prorrateada;
- previa confirmación de pago.

El cambio no deberá eliminar datos.

---

# 29. Downgrade de Plan

El Administrador podrá solicitar bajar de Plan.

El sistema deberá comprobar:

- Usuarios actuales;
- Gestores actuales;
- almacenamiento;
- documentos;
- funcionalidades en uso;
- integraciones;
- límites.

Si el Tenant supera el nuevo Plan:

DOWNGRADE_PENDING

El Administrador deberá ajustar su uso antes de completar el cambio.

---

# 30. Prorrateo

Cuando corresponda, FACT CENTRAL podrá calcular:

- crédito por periodo no utilizado;
- importe del nuevo Plan;
- diferencia;
- saldo a favor;
- saldo pendiente.

El algoritmo de prorrateo deberá ser configurable.

---

# 31. Descuentos

Podrán existir:

- descuento promocional;
- descuento anual;
- descuento por volumen;
- cupón;
- descuento manual autorizado;
- descuento por alianza;
- precio especial.

Cada descuento tendrá:

- código;
- tipo;
- valor;
- vigencia;
- cantidad de usos;
- Plan aplicable;
- Tenant aplicable;
- estado.

---

# 32. Periodo de gracia

Cuando una Suscripción vence sin pago:

ACTIVE
→ GRACE_PERIOD

Durante el periodo de gracia se podrá permitir:

- iniciar sesión;
- consultar información;
- pagar;
- descargar;
- exportar;
- recibir alertas;
- carga limitada.

La duración será configurable.

Ejemplo:

3, 5, 7 o 15 días.

---

# 33. Restricciones durante gracia

El Plan podrá definir:

- permitir nuevas cargas;
- permitir procesamiento;
- permitir solo lectura;
- limitar OCR;
- bloquear IA;
- bloquear nuevas invitaciones;
- bloquear nuevos Usuarios;
- bloquear nuevas integraciones.

---

# 34. Vencimiento

Cuando finaliza el periodo de gracia:

GRACE_PERIOD
→ SUSPENDED

La suspensión deberá ser automática si no existe pago confirmado.

---

# 35. Suspensión

Durante SUSPENDED:

- se bloquean nuevas cargas;
- se bloquea procesamiento;
- se bloquean invitaciones;
- se bloquean cambios operativos;
- se mantiene consulta limitada;
- se conserva información;
- se permite pagar;
- se permite solicitar exportación según política.

Suspender no significa eliminar.

---

# 36. Modo solo lectura

READ_ONLY permitirá:

- iniciar sesión;
- consultar Clientes;
- consultar Proveedores;
- consultar documentos;
- consultar expedientes;
- descargar archivos;
- exportar información autorizada.

No permitirá:

- cargar;
- editar;
- borrar;
- procesar;
- emitir alertas nuevas;
- modificar configuración;
- crear Usuarios;
- ejecutar nuevas operaciones.

---

# 37. Reactivación

Cuando se confirma el pago:

SUSPENDED
→ ACTIVE

El sistema deberá:

- restaurar permisos;
- reactivar Workers;
- reactivar integraciones;
- reactivar colas;
- reactivar procesamiento;
- conservar historial;
- registrar la reactivación;
- notificar al Administrador.

---

# 38. Cancelación

El Administrador podrá cancelar la renovación.

CANCELLED podrá significar:

- continuar hasta fin del periodo;
- no renovar;
- pasar luego a READ_ONLY;
- pasar luego a SUSPENDED.

La cancelación no elimina datos automáticamente.

---

# 39. Reembolso

El Superadmin podrá gestionar reembolsos.

Estados:

REFUND_REQUESTED

REFUND_APPROVED

REFUND_REJECTED

REFUNDED

PARTIALLY_REFUNDED

El reembolso no necesariamente cambia el estado del Tenant de inmediato.

---

# 40. Contracargos

Cuando exista un chargeback:

CHARGEBACK

FACT CENTRAL podrá:

- marcar el pago;
- notificar al Administrador;
- suspender renovación;
- poner el Tenant en revisión;
- bloquear cambios sensibles;
- solicitar documentación.

---

# 41. Suscripción por Administrador

La Suscripción se asigna al Tenant administrado por un Administrador Propietario.

No se crea una Suscripción por:

- Cliente;
- Proveedor;
- Usuario;
- Gestor;
- Empresa receptora;
- Empresa emisora.

La Suscripción cubre todo el espacio de trabajo del Tenant,
sujeto a los límites del Plan.

---

# 42. Múltiples Administradores

Un Tenant podrá tener:

- un Administrador Propietario;
- Administradores adicionales autorizados.

La Suscripción seguirá perteneciendo al Tenant.

No se duplicará por cada Administrador adicional.

---

# 43. Facturación SaaS

FACT CENTRAL deberá registrar:

- Plan;
- periodo;
- importe;
- impuestos;
- descuentos;
- moneda;
- estado;
- comprobante;
- método de pago;
- fecha de pago;
- referencia.

La facturación SaaS será independiente del módulo de pagos
a Usuarios dentro del ERP.

---

# 44. Separación de pagos

Debe quedar completamente separado:

## Pagos SaaS

El Administrador paga por usar FACT CENTRAL.

## Pagos ERP

El Gerente paga comisiones o montos preparados a Usuarios.

Son módulos distintos.

No deberán compartir saldos, cuentas ni comprobantes.

---

# 45. Panel del Administrador

El Administrador verá:

MI SUSCRIPCIÓN

Plan actual

Estado

Fecha de inicio

Fecha de vencimiento

Próxima renovación

Consumo

Cuotas

Complementos

Método de pago

Historial

Botones:

- Cambiar Plan;
- Pagar;
- Renovar;
- Descargar comprobante;
- Ver consumo;
- Comprar capacidad;
- Cancelar renovación.

---

# 46. Panel del Superadmin

Superadmin podrá ver:

- Tenants por estado;
- ingresos;
- suscripciones activas;
- pruebas;
- vencimientos;
- morosidad;
- consumo;
- upgrades;
- downgrades;
- cancelaciones;
- reactivaciones;
- reembolsos;
- errores de pago;
- riesgos de fraude.

---

# 47. Notificaciones

El Administrador recibirá avisos sobre:

- inicio de prueba;
- prueba próxima a vencer;
- prueba vencida;
- pago generado;
- pago confirmado;
- pago rechazado;
- renovación;
- vencimiento;
- periodo de gracia;
- suspensión;
- reactivación;
- consumo elevado;
- cuota agotada;
- upgrade;
- downgrade;
- cancelación;
- reembolso.

Canales:

- FACT CENTRAL;
- correo;
- SMS;
- WhatsApp.

---

# 48. Webhooks

Las pasarelas de pago podrán notificar mediante Webhooks.

Todo Webhook deberá:

- validar firma;
- validar origen;
- evitar duplicados;
- registrar evento;
- relacionar pago;
- actualizar estado;
- ser idempotente.

Un mismo evento recibido varias veces no deberá duplicar pagos.

---

# 49. Idempotencia

Una confirmación de pago repetida deberá producir un solo resultado.

Ejemplo:

1 pago confirmado
=
1 renovación
=
1 periodo

No deberá crear múltiples periodos por Webhooks repetidos.

---

# 50. Seguridad

Los procesos de Suscripción deberán proteger:

- importes;
- métodos de pago;
- referencias;
- tokens;
- Webhooks;
- credenciales;
- comprobantes;
- datos bancarios;
- historial.

Las tarjetas no deberán almacenarse directamente
si la pasarela puede tokenizarlas.

---

# 51. Auditoría

Toda acción registrará:

- tenant_id;
- subscription_id;
- plan_id;
- periodo;
- acción;
- persona;
- fecha;
- hora;
- importe;
- estado anterior;
- estado nuevo;
- pasarela;
- referencia;
- resultado.

---

# 52. Historial

Nunca se eliminará el historial de:

- Planes utilizados;
- cambios de precio;
- renovaciones;
- pagos;
- suspensiones;
- reactivaciones;
- cuotas;
- consumos;
- descuentos;
- cancelaciones.

---

# 53. Versionado de Planes

Un Plan podrá cambiar de precio o límites.

Pero una Suscripción histórica deberá conservar:

- nombre del Plan;
- precio;
- cuotas;
- condiciones;
- versión;
- vigencia.

No se reescribirán periodos anteriores.

---

# 54. Planes personalizados

Superadmin podrá crear un Plan personalizado para un Tenant.

Ejemplo:

PLAN CORPORATIVO NEXOMAR

Usuarios: 50

Gestores: 500

Documentos: 500,000

Storage: 10 TB

Soporte: prioritario

El Plan personalizado deberá quedar versionado.

---

# 55. SLA

Los Planes podrán definir un nivel de servicio.

Ejemplos:

- disponibilidad;
- prioridad;
- soporte;
- tiempo de respuesta;
- recuperación;
- procesamiento;
- backups;
- retención.

El SLA será contractual y medible.

---

# 56. Consumo de almacenamiento

El Storage deberá medir:

- archivos originales;
- versiones;
- derivados;
- miniaturas;
- OCR;
- evidencias;
- backups atribuibles;
- temporales.

Podrán excluirse del cobro algunos recursos internos.

---

# 57. Archivos temporales

Los archivos temporales deberán eliminarse automáticamente
según política.

No deberán consumir indefinidamente la cuota del Tenant.

---

# 58. Retención histórica

Cada Plan podrá definir cuánto historial mantiene disponible.

Ejemplo:

BÁSICO:
12 meses.

EMPRESA:
36 meses.

CORPORATIVO:
ilimitado o configurable.

El historial archivado podrá requerir recuperación especial.

---

# 59. API

La API de Suscripciones deberá permitir:

- ver Planes;
- ver Suscripción;
- ver consumo;
- generar pago;
- confirmar pago;
- cambiar Plan;
- comprar complemento;
- cancelar renovación;
- solicitar reactivación.

Cada acción deberá validar permisos.

---

# 60. Workers

Los Workers deberán comprobar:

- estado del Tenant;
- estado de Suscripción;
- cuota disponible;
- Plan habilitado;
- prioridad.

Un Worker no deberá procesar nuevos trabajos
para un Tenant suspendido.

---

# 61. Colas

Las colas podrán usar prioridad por Plan.

Ejemplo:

BÁSICO
→ prioridad normal.

EMPRESA
→ prioridad alta.

CORPORATIVO
→ prioridad superior.

La prioridad no deberá eliminar la equidad entre Tenants.

---

# 62. NEXUS

NEXUS podrá:

- predecir crecimiento de consumo;
- alertar sobre cuotas;
- recomendar Upgrade;
- detectar uso anómalo;
- detectar abuso;
- proyectar almacenamiento;
- proponer escalado.

NEXUS no podrá cambiar un Plan sin autorización.

---

# 63. Fraude y abuso

FACT CENTRAL podrá detectar:

- múltiples pruebas fraudulentas;
- cuentas repetidas;
- consumo anómalo;
- métodos de pago rechazados;
- chargebacks;
- automatización abusiva;
- creación masiva de Tenants;
- ataques contra cuotas.

El sistema podrá:

- bloquear temporalmente;
- solicitar verificación;
- limitar uso;
- escalar a Superadmin.

---

# 64. Eliminación de Suscripción

Cerrar una Suscripción no elimina inmediatamente el Tenant.

La secuencia será:

SUSCRIPCIÓN CERRADA
↓
TENANT READ_ONLY O SUSPENDED
↓
PERIODO DE RETENCIÓN
↓
EXPORTACIÓN
↓
ELIMINACIÓN SEGÚN POLÍTICA

---

# 65. Regla de continuidad

La falta de pago podrá suspender funciones,
pero no deberá destruir los documentos del Tenant.

La información seguirá protegida por:

- almacenamiento;
- replicación;
- backups;
- retención;
- auditoría.

---

# 66. Regla de escalabilidad

El Motor de Suscripciones deberá soportar:

- 10 Tenants;
- 100 Tenants;
- 1,000 Tenants;
- 100,000 Tenants;
- millones de operaciones.

Sin modificar la lógica principal.

---

# 67. Flujo general

CREAR TENANT
↓
ASIGNAR TRIAL
↓
MEDIR CONSUMO
↓
ELEGIR PLAN
↓
GENERAR PAGO
↓
CONFIRMAR
↓
ACTIVAR SUSCRIPCIÓN
↓
CONSUMIR CUOTAS
↓
RENOVAR
↓
GRACIA SI NO PAGA
↓
SUSPENDER
↓
REACTIVAR
↓
CANCELAR O CONTINUAR

---

# 68. Reglas supremas

## Regla Suprema 1

TODA SUSCRIPCIÓN PERTENECE A UN TENANT.

## Regla Suprema 2

LA SUSCRIPCIÓN NO PERTENECE A UNA EMPRESA RECEPTORA,
PROVEEDOR, USUARIO O GESTOR.

## Regla Suprema 3

TODO PLAN DEBERÁ ESTAR VERSIONADO.

## Regla Suprema 4

TODO CONSUMO DEBERÁ SER MEDIBLE Y AUDITABLE.

## Regla Suprema 5

LOS LÍMITES PODRÁN SER SUAVES, DUROS O FACTURABLES.

## Regla Suprema 6

LA SUSPENSIÓN NO ELIMINA DATOS.

## Regla Suprema 7

LA REACTIVACIÓN CONSERVA TODO EL HISTORIAL.

## Regla Suprema 8

LOS PAGOS SaaS SON INDEPENDIENTES DE LOS PAGOS DEL ERP.

## Regla Suprema 9

LOS WEBHOOKS DE PAGO DEBERÁN SER VALIDADOS E IDEMPOTENTES.

## Regla Suprema 10

NINGÚN CAMBIO DE PLAN DEBERÁ REESCRIBIR PERIODOS HISTÓRICOS.

## Regla Suprema 11

EL ADMINISTRADOR PROPIETARIO CONTROLA LA SUSCRIPCIÓN DEL TENANT.

## Regla Suprema 12

FACT CENTRAL PODRÁ CRECER SIN MODIFICAR EL ALGORITMO DE SUSCRIPCIONES.
 
