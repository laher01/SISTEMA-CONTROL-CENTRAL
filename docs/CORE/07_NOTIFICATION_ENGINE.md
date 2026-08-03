# 07_NOTIFICATION_ENGINE.md

# FACT CENTRAL SaaS

## NOTIFICATION ENGINE

Versión 1.0

---

# 1. Objetivo

Definir el Motor Oficial de Notificaciones de FACT CENTRAL.

El Notification Engine será responsable de:

- recibir solicitudes de notificación;
- determinar destinatarios;
- seleccionar canales;
- aplicar preferencias;
- aplicar prioridades;
- aplicar reglas de seguridad;
- generar mensajes;
- enviar;
- reintentar;
- confirmar entrega;
- registrar lectura;
- escalar;
- evitar duplicados;
- auditar todo el proceso.

Ningún otro módulo deberá enviar mensajes directamente.

---

# 2. Principio fundamental

Los demás motores determinan que algo debe comunicarse.

El Notification Engine determina:

```text
A QUIÉN
+
POR QUÉ CANAL
+
EN QUÉ MOMENTO
+
CON QUÉ PRIORIDAD
+
CON QUÉ CONTENIDO
```

---

# 3. Separación de responsabilidades

## Rule Engine

Determina si corresponde notificar.

## Workflow Engine

Coordina el proceso.

## Time Engine

Determina cuándo debe enviarse.

## Event Bus

Transporta eventos.

## Permission Engine

Determina quién puede recibir o visualizar información.

## Notification Engine

Construye, envía, reintenta y registra la notificación.

## NEXUS

Puede sugerir prioridad, resumen y destinatarios.

---

# 4. Canales oficiales

FACT CENTRAL podrá utilizar:

- bandeja interna;
- correo electrónico;
- SMS;
- WhatsApp;
- Push;
- Web Push;
- notificación móvil futura;
- webhook autorizado;
- otros canales aprobados.

La bandeja interna será el canal oficial mínimo.

Los canales externos serán complementarios.

---

# 5. Fuente oficial

La bandeja interna de FACT CENTRAL será la fuente oficial
de notificaciones del sistema.

Correo, SMS, WhatsApp y Push podrán fallar.

Una notificación crítica deberá quedar registrada
aunque un canal externo no responda.

---

# 6. Entidades principales

El Notification Engine deberá manejar:

- notification;
- notification_request;
- notification_recipient;
- notification_channel;
- notification_delivery;
- notification_template;
- notification_preference;
- notification_attempt;
- notification_batch;
- notification_escalation;
- notification_acknowledgement;
- notification_digest;
- notification_suppression;
- notification_audit.

---

# 7. Solicitud de notificación

Toda solicitud deberá contener:

- notification_request_id;
- tenant_id;
- event_id;
- correlation_id;
- causation_id;
- source_engine;
- notification_type;
- severity;
- priority;
- resource_type;
- resource_id;
- recipient_scope;
- requested_channels;
- template_code;
- template_version;
- data;
- scheduled_at;
- expires_at;
- idempotency_key;
- created_at.

---

# 8. Estados oficiales

Toda notificación podrá estar en:

```text
CREATED
QUEUED
SCHEDULED
PROCESSING
SENT
PARTIALLY_SENT
DELIVERED
READ
ACKNOWLEDGED
FAILED
RETRYING
EXPIRED
CANCELLED
SUPPRESSED
ESCALATED
ARCHIVED
```

---

# 9. Estados por canal

Cada canal tendrá su propio estado:

```text
PENDING
QUEUED
SENT
DELIVERED
READ
FAILED
RETRYING
BOUNCED
REJECTED
EXPIRED
CANCELLED
```

---

# 10. Flujo general

```text
EVENTO O SOLICITUD
        ↓
VALIDAR TENANT
        ↓
VALIDAR DESTINATARIOS
        ↓
VALIDAR PERMISOS
        ↓
APLICAR PREFERENCIAS
        ↓
SELECCIONAR CANALES
        ↓
CONSTRUIR MENSAJE
        ↓
ENVIAR
        ↓
CONFIRMAR ENTREGA
        ↓
REINTENTAR SI FALLA
        ↓
ESCALAR SI CORRESPONDE
        ↓
AUDITAR
```

---

# 11. Tipos de notificación

## INFORMATION

Información general.

## SUCCESS

Confirmación de operación.

## WARNING

Advertencia.

## ERROR

Error operativo.

## CRITICAL

Incidente crítico.

## ACTION_REQUIRED

Requiere acción humana.

## APPROVAL_REQUIRED

Requiere aprobación.

## DEADLINE

Vencimiento o plazo.

## SECURITY

Evento de seguridad.

## COMPLIANCE

Cumplimiento tributario o documental.

## PAYMENT

Pago o liquidación.

## SUBSCRIPTION

Suscripción SaaS.

## SYSTEM_HEALTH

Estado técnico.

---

# 12. Severidad

Los niveles serán:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 13. Prioridad

Las prioridades serán:

```text
IMMEDIATE
URGENT
HIGH
NORMAL
LOW
BACKGROUND
```

---

# 14. Relación entre severidad y prioridad

Una notificación crítica normalmente tendrá prioridad alta.

Sin embargo, severidad y prioridad no son lo mismo.

Ejemplo:

```text
Incidente crítico ya resuelto
→ severidad CRITICAL
→ prioridad NORMAL para informe posterior
```

---

# 15. Destinatarios

Los destinatarios podrán resolverse por:

- persona;
- rol;
- Usuario;
- Gestor;
- Administrador;
- Gerente;
- Secretaría;
- grupo;
- relación con Cliente;
- relación con Proveedor;
- relación con Expediente;
- responsable de tarea;
- suscripción;
- equipo técnico;
- Superadmin.

---

# 16. Resolución de destinatarios

Ejemplo:

```text
Secretaría detecta error documental
        ↓
Documento
        ↓
Proveedor
        ↓
Usuario
        ↓
Gestor relacionado
        ↓
Administrador
```

Secretaría no necesitará conocer
la estructura completa de relaciones.

El sistema resolverá internamente los destinatarios.

---

# 17. Alcance de destinatario

Los alcances podrán ser:

```text
SELF
OWNER
RESPONSIBLE
RELATED_USER
RELATED_MANAGER
TENANT_ADMINS
TENANT_ROLE
PLATFORM_ADMIN
CUSTOM_GROUP
```

---

# 18. Privacidad

El contenido deberá ajustarse al permiso del destinatario.

Ejemplo:

Administrador:

```text
Proveedor:
LABERTEC

Usuario:
WILLI01

Gestor:
GESTOR-001

Documento:
F001-250
```

Secretaría:

```text
Proveedor:
LABERTEC

Documento:
F001-250
```

Gestor:

```text
Documento observado:
F001-250

Acción requerida:
Adjuntar Voucher
```

Cada rol recibirá únicamente la información necesaria.

---

# 19. Regla de datos mínimos

Una notificación no deberá contener más información
de la necesaria para cumplir su objetivo.

No se enviarán por canales externos:

- contraseñas;
- tokens;
- CVV;
- claves;
- cuentas bancarias completas;
- documentos fiscales completos;
- información sensible innecesaria;
- enlaces permanentes.

---

# 20. Bandeja interna

Toda notificación relevante deberá registrarse
en la bandeja interna.

La bandeja deberá permitir:

- listar;
- filtrar;
- buscar;
- marcar como leída;
- confirmar recepción;
- responder;
- abrir recurso;
- archivar;
- silenciar;
- consultar historial.

---

# 21. Notificación interna

Toda notificación interna deberá contener:

- título;
- resumen;
- cuerpo;
- categoría;
- severidad;
- prioridad;
- fecha;
- recurso relacionado;
- acción requerida;
- fecha límite;
- estado;
- destinatario;
- origen;
- trazabilidad.

---

# 22. Correo electrónico

El correo podrá utilizarse para:

- alertas;
- recordatorios;
- aprobaciones;
- informes;
- confirmaciones;
- recuperación;
- seguridad;
- suscripciones;
- Billing.

---

# 23. WhatsApp

WhatsApp podrá utilizarse para:

- avisos urgentes;
- recordatorios;
- alertas operativas;
- confirmaciones;
- solicitudes de documentos;
- estados de cumplimiento.

Solo se utilizarán integraciones autorizadas.

No se deberán utilizar automatizaciones no oficiales.

---

# 24. SMS

SMS podrá utilizarse para:

- códigos;
- MFA;
- alertas críticas;
- recuperación;
- confirmaciones urgentes.

---

# 25. Push

Push podrá utilizarse para:

- alertas inmediatas;
- tareas;
- vencimientos;
- pagos;
- incidentes;
- mensajes de seguridad.

---

# 26. Webhooks

Los Webhooks de salida podrán utilizarse para integraciones autorizadas.

Cada Webhook deberá:

- estar registrado;
- estar firmado;
- tener secreto;
- utilizar HTTPS;
- registrar intentos;
- aplicar reintentos;
- validar respuesta;
- usar idempotencia.

---

# 27. Selección de canales

La selección dependerá de:

- tipo de notificación;
- severidad;
- prioridad;
- preferencias;
- rol;
- Plan;
- disponibilidad;
- horario;
- configuración del Tenant;
- normativa;
- emergencia.

---

# 28. Canal obligatorio

La bandeja interna será obligatoria para:

- alertas;
- tareas;
- vencimientos;
- aprobaciones;
- pagos;
- seguridad;
- cumplimiento;
- errores críticos.

---

# 29. Canal complementario

Correo, WhatsApp, SMS y Push podrán complementar
la bandeja interna.

Una falla externa no eliminará la notificación interna.

---

# 30. Preferencias del Usuario

Cada Persona podrá configurar:

- canales preferidos;
- horarios;
- tipos de notificación;
- resúmenes;
- idioma;
- frecuencia;
- silencio temporal;
- nivel mínimo de prioridad.

---

# 31. Preferencias no modificables

No podrán desactivarse completamente:

- seguridad crítica;
- MFA;
- cambios de credenciales;
- alertas legales obligatorias;
- suspensión;
- eliminación;
- pagos críticos;
- incidentes de Tenant;
- avisos exigidos por política.

---

# 32. Preferencias por Tenant

Las preferencias podrán variar entre Tenants.

Una Persona podrá recibir:

- notificaciones completas en Tenant A;
- solo bandeja interna en Tenant B.

---

# 33. Horarios de silencio

Podrán configurarse horarios de silencio.

Ejemplo:

```text
22:00 a 07:00
```

Durante ese periodo:

- se retienen notificaciones normales;
- se agrupan;
- se envían después;
- las críticas pueden salir inmediatamente.

---

# 34. Excepción crítica

Las notificaciones CRITICAL podrán ignorar
el horario de silencio cuando la política lo permita.

---

# 35. Plantillas

Toda notificación utilizará plantillas versionadas.

Cada plantilla tendrá:

- template_id;
- code;
- version;
- title;
- body;
- channels;
- language;
- variables;
- status;
- effective_from;
- effective_to;
- tenant_id, cuando corresponda.

---

# 36. Ejemplo de plantilla

```text
Código:
EXPEDIENT.VOUCHER_REQUIRED

Título:
Voucher pendiente

Cuerpo:
El Expediente {{expedient_code}}
requiere un Voucher validado.

Fecha límite:
{{deadline}}
```

---

# 37. Versionado de plantillas

Las plantillas no deberán editarse
destruyendo versiones anteriores.

Una notificación histórica conservará
la versión utilizada.

---

# 38. Variables

Las variables deberán estar:

- definidas;
- validadas;
- escapadas;
- limitadas;
- asociadas a permisos.

No se permitirá código libre.

---

# 39. Idioma

Cada Tenant y Persona podrá tener idioma preferido.

El sistema podrá seleccionar:

- español;
- inglés;
- otros idiomas futuros.

La ausencia de traducción utilizará
una plantilla de respaldo.

---

# 40. Construcción de mensajes

El Notification Engine deberá construir mensajes
a partir de:

- plantilla;
- datos;
- rol;
- permisos;
- canal;
- idioma;
- formato;
- severidad.

---

# 41. Mensajes por canal

Una misma notificación podrá tener versiones distintas.

Ejemplo:

## Bandeja interna

Mensaje completo.

## Correo

Resumen con enlace seguro.

## WhatsApp

Texto breve.

## SMS

Texto mínimo.

## Push

Título y acción.

---

# 42. Enlaces

Los enlaces deberán:

- ser temporales cuando corresponda;
- requerir autenticación;
- respetar Tenant;
- respetar permisos;
- no exponer identificadores sensibles;
- no permitir acceso directo al Storage.

---

# 43. Acciones rápidas

Una notificación podrá ofrecer:

- revisar;
- aprobar;
- rechazar;
- adjuntar;
- responder;
- abrir Expediente;
- abrir pago;
- ver alerta;
- marcar resuelto.

Las acciones deberán volver al Backend
y validar permisos.

---

# 44. Notificación de alerta documental

Ejemplo:

```text
Documento observado:
Factura F001-250

Motivo:
Voucher faltante

Responsables:
Usuario
Gestor relacionado
Administrador

Canales:
Bandeja interna
Correo
WhatsApp según configuración
```

---

# 45. Notificación de SSCO

Ejemplo:

```text
ALERTA CRÍTICA

Proveedor detectado en SSCO

Proveedor:
{{supplier_name}}

RUC:
{{supplier_tax_id}}

Periodo:
{{period}}

Acción:
Suspender nuevas asignaciones
y revisar operaciones relacionadas.
```

---

# 46. Notificación ITF

Ejemplo:

```text
Reporte ITF pendiente

Proveedor:
{{supplier_name}}

Periodo:
{{period}}

Fecha límite:
{{deadline}}
```

---

# 47. Notificación PDT

Ejemplo:

```text
PDT mensual pendiente

Proveedor:
{{supplier_name}}

Periodo:
{{period}}

Estado:
No presentado
```

---

# 48. Notificación de pedido excedido

Ejemplo:

```text
PEDIDO EXCEDIDO

Cliente:
{{client_name}}

Proveedor:
{{supplier_name}}

Asignado:
{{assigned_amount}}

Ejecutado:
{{executed_amount}}

Exceso:
{{excess_amount}}
```

---

# 49. Notificación de concentración

Ejemplo:

```text
Concentración elevada

Proveedor:
{{supplier_name}}

Participación:
{{percentage}}

Límite:
{{limit}}

Acción sugerida:
Redistribuir compras.
```

---

# 50. Notificación de Expediente incompleto

Ejemplo:

```text
Expediente incompleto

Expediente:
{{expedient_code}}

Documentos faltantes:
{{missing_documents}}

Fecha límite:
{{deadline}}
```

---

# 51. Notificación de liquidación

El Usuario podrá recibir:

```text
Liquidación provisional disponible

Periodo:
{{period}}

Producción:
{{production_amount}}

Comisión:
{{commission_amount}}

Saldo:
{{balance}}
```

No deberá recibir fórmulas reservadas
si no tiene permiso.

---

# 52. Notificación de pago

El Usuario podrá recibir:

```text
Pago ejecutado

Periodo:
{{period}}

Importe:
{{amount}}

Estado:
{{status}}
```

---

# 53. Notificación de cuenta bancaria

Ejemplo:

```text
Cuenta de pago sin verificar

Banco:
{{bank_name}}

Estado:
Pendiente de confirmación
```

---

# 54. Notificación SaaS

El Administrador podrá recibir:

- Trial próximo a vencer;
- renovación;
- pago confirmado;
- pago fallido;
- periodo de gracia;
- suspensión;
- reactivación;
- cuota agotada;
- cambio de Plan.

---

# 55. Notificación de seguridad

Ejemplos:

- inicio de sesión desconocido;
- cambio de contraseña;
- cambio de correo;
- cambio de celular;
- MFA desactivado;
- múltiples intentos fallidos;
- acceso sospechoso;
- exportación total;
- eliminación solicitada.

---

# 56. Notificación de infraestructura

Superadmin podrá recibir:

- nodo offline;
- Storage degradado;
- backup fallido;
- DLQ elevada;
- latencia crítica;
- CPU anormal;
- posible minería;
- corrupción;
- reloj desincronizado;
- cola detenida.

---

# 57. Lotes

El sistema podrá enviar notificaciones en lotes.

Ejemplos:

- reportes mensuales;
- obligaciones pendientes;
- resumen de alertas;
- resumen de producción;
- resumen de cumplimiento.

---

# 58. Digest

Un Digest agrupa notificaciones.

Tipos posibles:

```text
DAILY
WEEKLY
MONTHLY
CUSTOM
```

---

# 59. Digest diario

Ejemplo:

```text
Resumen diario

Alertas nuevas: 5
Expedientes incompletos: 8
Vouchers pendientes: 3
Pedidos excedidos: 2
```

---

# 60. Notificaciones individuales obligatorias

No deberán agruparse:

- seguridad crítica;
- SSCO;
- pago ejecutado;
- eliminación;
- suspensión;
- acceso sospechoso;
- conflicto fiscal;
- malware;
- incidente crítico.

---

# 61. Idempotencia

Una misma solicitud no deberá generar
múltiples notificaciones iguales.

La clave podrá incluir:

```text
tenant_id
+
notification_type
+
resource_id
+
recipient_id
+
period
+
event_id
```

---

# 62. Duplicados

Si el mismo evento se consume dos veces:

- se reconocerá la idempotency_key;
- no se creará otra notificación;
- se devolverá el resultado existente.

---

# 63. Ventana de deduplicación

Podrá existir una ventana configurable.

Ejemplo:

```text
No enviar la misma alerta
más de una vez en 30 minutos
```

Las notificaciones críticas podrán seguir
una política distinta.

---

# 64. Supresión

Una notificación podrá ser suprimida cuando:

- ya fue resuelta;
- existe otra más reciente;
- forma parte de un Digest;
- está duplicada;
- fue cancelada;
- el recurso dejó de existir;
- la política lo permite.

---

# 65. Supresión auditada

Toda supresión deberá registrar:

- motivo;
- regla;
- actor;
- fecha;
- notificación reemplazante;
- estado.

---

# 66. Envío

Cada canal deberá utilizar un adaptador independiente.

Ejemplo:

```text
NOTIFICATION ENGINE
├── INTERNAL
├── EMAIL
├── SMS
├── WHATSAPP
├── PUSH
└── WEBHOOK
```

---

# 67. Contrato de adaptador

Todo adaptador deberá exponer:

- send;
- get_status;
- cancel, cuando corresponda;
- validate_callback;
- handle_webhook;
- retry;
- health_check.

---

# 68. Reintentos

Cada canal tendrá su política.

Ejemplo:

```text
Intento 1:
inmediato

Intento 2:
1 minuto

Intento 3:
5 minutos

Intento 4:
30 minutos

Intento 5:
2 horas
```

---

# 69. Errores reintentables

Ejemplos:

- timeout;
- proveedor caído;
- error temporal;
- conexión fallida;
- rate limit;
- respuesta incompleta.

---

# 70. Errores no reintentables

Ejemplos:

- número inválido;
- correo inexistente;
- plantilla inválida;
- destinatario bloqueado;
- permiso denegado;
- canal no autorizado.

---

# 71. Fallback

Si un canal falla,
podrá utilizarse otro.

Ejemplo:

```text
WhatsApp falla
↓
Correo
↓
Bandeja interna permanece
```

---

# 72. Canal de respaldo

Cada tipo de notificación podrá definir:

- canal primario;
- canal secundario;
- canal obligatorio;
- canal de emergencia.

---

# 73. Confirmación de entrega

Los proveedores externos podrán informar:

```text
SENT
DELIVERED
READ
FAILED
BOUNCED
```

El sistema deberá validar los Webhooks
antes de actualizar estados.

---

# 74. Lectura interna

La bandeja interna registrará:

- delivered_at;
- opened_at;
- read_at;
- acknowledged_at;
- action_taken_at.

---

# 75. Acknowledgement

Algunas notificaciones exigirán confirmación.

Ejemplos:

- alerta crítica;
- cambio de cuenta;
- pago preparado;
- incidente de seguridad;
- SSCO;
- conflicto fiscal.

---

# 76. Estados de confirmación

```text
NOT_REQUIRED
PENDING
ACKNOWLEDGED
REJECTED
EXPIRED
ESCALATED
```

---

# 77. Escalamiento

Si no existe respuesta:

```text
NOTIFICACIÓN
↓
ESPERAR
↓
NO CONFIRMADA
↓
ESCALAR
```

---

# 78. Ejemplo de escalamiento

```text
Gestor recibe observación
↓
24 horas sin respuesta
↓
Usuario
↓
24 horas adicionales
↓
Administrador
```

---

# 79. Integración con Time Engine

El Time Engine controlará:

- envío programado;
- recordatorios;
- reintentos temporales;
- horarios de silencio;
- vencimientos;
- escalamiento;
- Digests;
- expiración.

---

# 80. Integración con Workflow Engine

El Workflow Engine podrá solicitar:

```text
notification.requested
```

y esperar:

```text
notification.acknowledged
```

---

# 81. Integración con Rule Engine

El Rule Engine podrá determinar:

- si corresponde notificar;
- severidad;
- prioridad;
- destinatarios;
- obligatoriedad;
- necesidad de escalamiento;
- canales mínimos.

---

# 82. Integración con Event Bus

Eventos posibles:

```text
notification.requested
notification.created
notification.queued
notification.sent
notification.delivered
notification.read
notification.acknowledged
notification.failed
notification.retried
notification.expired
notification.escalated
notification.suppressed
```

---

# 83. Integración con Permission Engine

Antes de generar contenido deberá validarse:

- Tenant;
- destinatario;
- rol;
- permiso;
- relación;
- alcance;
- sensibilidad.

---

# 84. Integración con NEXUS

NEXUS podrá:

- resumir información;
- priorizar alertas;
- sugerir destinatarios;
- detectar fatiga de notificaciones;
- recomendar agrupación;
- detectar mensajes ignorados;
- proponer mejores horarios.

NEXUS no podrá:

- ocultar alertas críticas;
- eliminar notificaciones;
- cambiar destinatarios protegidos;
- enviar información sensible sin permiso;
- modificar estados oficiales.

---

# 85. Fatiga de notificaciones

El sistema deberá evitar:

- mensajes repetitivos;
- exceso de alertas;
- múltiples avisos por el mismo hecho;
- canales innecesarios;
- mensajes sin acción.

---

# 86. Control de frecuencia

Podrán aplicarse límites como:

- máximo por hora;
- máximo por tipo;
- máximo por recurso;
- agrupación;
- Digest;
- prioridad mínima.

---

# 87. Excepción a frecuencia

Las notificaciones críticas podrán ignorar
límites normales.

---

# 88. Notificaciones masivas

Las notificaciones masivas deberán:

- usar lotes;
- respetar límites;
- registrar destinatarios;
- permitir cancelación;
- evitar duplicados;
- proteger datos;
- controlar costos;
- monitorear fallos.

---

# 89. Costos

El sistema deberá medir:

- SMS enviados;
- mensajes WhatsApp;
- correos;
- Push;
- Webhooks;
- costo por Tenant;
- costo por Plan;
- costo por tipo.

---

# 90. Cuotas

Los Planes podrán limitar:

- SMS;
- WhatsApp;
- correos masivos;
- Push;
- Webhooks;
- plantillas personalizadas.

La bandeja interna no deberá depender
de un proveedor externo.

---

# 91. Notificación ante cuota agotada

Si se agota una cuota externa:

- se mantiene bandeja interna;
- se genera alerta al Administrador;
- se aplica fallback;
- se registra el incidente;
- se evita perder la solicitud.

---

# 92. Plantillas protegidas

Las plantillas de:

- seguridad;
- Billing;
- suscripción;
- eliminación;
- MFA;
- privacidad;

no podrán modificarse libremente por un Tenant.

---

# 93. Plantillas del Tenant

El Administrador podrá personalizar plantillas permitidas:

- recordatorios;
- alertas operativas;
- solicitudes documentales;
- mensajes de bienvenida;
- avisos internos.

No podrá insertar código ejecutable.

---

# 94. Validación de plantilla

Antes de activar una plantilla se verificará:

- variables;
- longitud;
- formato;
- enlaces;
- contenido sensible;
- canal;
- idioma;
- compatibilidad;
- seguridad.

---

# 95. Vista previa

El Administrador podrá previsualizar:

- bandeja interna;
- correo;
- WhatsApp;
- SMS;
- Push.

---

# 96. Shadow Mode

Una regla de notificación podrá probarse
en modo sombra.

En Shadow Mode:

- se construye el mensaje;
- se registra el destinatario;
- no se envía;
- se mide el impacto;
- se detectan duplicados;
- se analiza volumen.

---

# 97. Simulación

El Administrador podrá simular:

- destinatarios;
- canales;
- costos;
- horarios;
- contenido;
- cantidad;
- escalamiento.

---

# 98. Cancelación

Una notificación podrá cancelarse
antes de ser enviada.

Después de enviada,
no podrá eliminarse del canal externo.

Podrá marcarse como:

```text
CANCELLED_AFTER_SEND
```

para auditoría.

---

# 99. Expiración

Una notificación podrá expirar.

Ejemplo:

```text
Aprobación válida hasta:
18:00
```

Después de expirar:

- se invalida la acción;
- se actualiza estado;
- se puede escalar;
- se conserva historial.

---

# 100. Incidentes de canal

Si un proveedor externo presenta fallos:

- se marca DEGRADED;
- se activa fallback;
- se reduce tráfico;
- se notifica a Superadmin;
- se conserva la cola;
- se reintenta según política.

---

# 101. Health Check

Se deberá revisar:

- bandeja interna;
- correo;
- SMS;
- WhatsApp;
- Push;
- Webhooks;
- colas;
- Workers;
- plantillas;
- callbacks;
- tasa de entrega;
- tasa de fallo.

---

# 102. Métricas

Se medirá:

- notificaciones creadas;
- enviadas;
- entregadas;
- leídas;
- confirmadas;
- fallidas;
- reintentadas;
- expiradas;
- escaladas;
- suprimidas;
- costo;
- latencia;
- tasa de lectura;
- tasa de acción.

---

# 103. Dashboard

El Administrador podrá ver:

```text
ENVIADAS
ENTREGADAS
LEÍDAS
PENDIENTES
FALLIDAS
REINTENTANDO
ESCALADAS
```

El Superadmin podrá ver métricas globales
sin exponer contenido innecesario.

---

# 104. Auditoría

Toda notificación deberá registrar:

- tenant_id;
- notification_id;
- request_id;
- event_id;
- recipient_id;
- role;
- channel;
- template;
- template_version;
- status;
- attempt;
- provider;
- timestamps;
- result;
- error;
- correlation_id;
- idempotency_key.

---

# 105. Historial

No se deberán sobrescribir silenciosamente:

- destinatarios;
- contenido;
- plantilla;
- estado;
- intentos;
- errores;
- entregas;
- confirmaciones;
- escalaciones.

---

# 106. Retención

Las notificaciones se conservarán según:

- tipo;
- criticidad;
- Plan;
- obligación;
- política;
- Tenant;
- normativa.

---

# 107. Seguridad

El Notification Engine deberá proteger:

- credenciales de proveedores;
- tokens;
- Webhooks;
- teléfonos;
- correos;
- contenido sensible;
- enlaces;
- plantillas;
- datos personales.

---

# 108. Secretos

Las credenciales de:

- correo;
- SMS;
- WhatsApp;
- Push;
- Webhooks;

no deberán almacenarse en texto plano
ni dentro del código.

---

# 109. Multi-Tenant

Toda notificación deberá pertenecer a un Tenant,
salvo notificaciones globales de plataforma.

No se permitirá:

- enviar datos de otro Tenant;
- resolver destinatarios cruzados;
- reutilizar plantillas privadas;
- mostrar contenido ajeno;
- mezclar colas lógicas.

---

# 110. Identidades técnicas

Los Workers de notificaciones utilizarán
identidades técnicas limitadas.

No tendrán acceso administrativo global
a la información operativa.

---

# 111. Recuperación

Después de una caída:

```text
LEER NOTIFICACIONES PENDIENTES
↓
VERIFICAR ESTADO DEL CANAL
↓
REANUDAR
↓
EVITAR DUPLICADOS
```

---

# 112. Persistencia

Las notificaciones críticas no dependerán
solo de memoria.

El estado deberá persistirse.

---

# 113. Respuesta perdida

Escenario:

```text
Proveedor acepta mensaje
↓
respuesta se pierde
↓
Worker reintenta
```

Resultado esperado:

- consultar estado;
- usar idempotencia;
- evitar envío duplicado cuando sea posible;
- conservar auditoría.

---

# 114. Pruebas obligatorias

Deberán existir pruebas para:

- correo caído;
- WhatsApp caído;
- SMS caído;
- Push caído;
- destinatario inválido;
- plantilla inválida;
- mensaje duplicado;
- Webhook repetido;
- confirmación perdida;
- escalamiento;
- silencio;
- crítica durante silencio;
- cuota agotada;
- múltiples Tenants;
- recuperación;
- fatiga;
- Digest;
- datos sensibles;
- permisos.

---

# 115. Prueba de duplicado

Escenario:

```text
Mismo event_id
consumido dos veces
```

Resultado esperado:

```text
una sola notificación lógica
```

---

# 116. Prueba de fallback

Escenario:

```text
WhatsApp falla
```

Resultado esperado:

```text
bandeja interna disponible
+
correo según política
+
auditoría
```

---

# 117. Prueba de privacidad

Escenario:

```text
Secretaría recibe alerta
```

Resultado esperado:

- ve documento;
- ve observación;
- no ve liquidación;
- no ve cuenta bancaria;
- no ve estructura reservada.

---

# 118. Prueba de escalamiento

Escenario:

```text
Gestor no confirma en 24 horas
```

Resultado esperado:

```text
Usuario notificado
↓
Administrador si persiste
```

---

# 119. Regla de separación

El Notification Engine comunica.

No decide:

- reglas fiscales;
- permisos;
- pagos;
- estados oficiales;
- cierres;
- liquidaciones;
- suspensión;
- eliminación.

---

# 120. Reglas Supremas

## Regla Suprema 1

NINGÚN MÓDULO ENVIARÁ MENSAJES DIRECTAMENTE.

## Regla Suprema 2

LA BANDEJA INTERNA SERÁ EL CANAL OFICIAL MÍNIMO.

## Regla Suprema 3

LOS CANALES EXTERNOS SERÁN COMPLEMENTARIOS.

## Regla Suprema 4

UNA FALLA EXTERNA NO ELIMINARÁ
LA NOTIFICACIÓN INTERNA.

## Regla Suprema 5

TODA NOTIFICACIÓN PERTENECE A UN TENANT,
SALVO LAS DE PLATAFORMA.

## Regla Suprema 6

TODA NOTIFICACIÓN SERÁ IDEMPOTENTE.

## Regla Suprema 7

LOS DUPLICADOS NO GENERARÁN MÚLTIPLES IMPACTOS.

## Regla Suprema 8

EL CONTENIDO RESPETARÁ EL ROL,
PERMISO Y RELACIÓN DEL DESTINATARIO.

## Regla Suprema 9

LAS NOTIFICACIONES NO EXPONDRÁN
INFORMACIÓN SENSIBLE INNECESARIA.

## Regla Suprema 10

LAS PLANTILLAS SERÁN VERSIONADAS.

## Regla Suprema 11

LAS NOTIFICACIONES CRÍTICAS NO PODRÁN
DESACTIVARSE COMPLETAMENTE.

## Regla Suprema 12

EL TIME ENGINE DETERMINA CUÁNDO.

## Regla Suprema 13

EL RULE ENGINE DETERMINA SI CORRESPONDE.

## Regla Suprema 14

EL WORKFLOW ENGINE COORDINA EL PROCESO.

## Regla Suprema 15

EL NOTIFICATION ENGINE DETERMINA
CÓMO SE COMUNICA.

## Regla Suprema 16

TODO INTENTO DE ENVÍO SERÁ AUDITABLE.

## Regla Suprema 17

LOS FALLOS TEMPORALES SERÁN REINTENTADOS
SEGÚN POLÍTICA.

## Regla Suprema 18

LOS FALLOS PERMANENTES NO SE REINTENTARÁN
INDEFINIDAMENTE.

## Regla Suprema 19

LAS NOTIFICACIONES CRÍTICAS PODRÁN ESCALARSE.

## Regla Suprema 20

NEXUS PODRÁ RECOMENDAR,
PERO NO OCULTAR ALERTAS CRÍTICAS.

## Regla Suprema 21

LAS CREDENCIALES DE CANALES EXTERNOS
NO ESTARÁN EN EL CÓDIGO.

## Regla Suprema 22

LA CAÍDA DE UN NODO NO DEBERÁ PERDER
NOTIFICACIONES PENDIENTES.

## Regla Suprema 23

TODA ACCIÓN DESDE UNA NOTIFICACIÓN
DEBERÁ SER VALIDADA NUEVAMENTE POR EL BACKEND.

## Regla Suprema 24

FACT CENTRAL EVITARÁ LA FATIGA
SIN SACRIFICAR SEGURIDAD NI CUMPLIMIENTO.
