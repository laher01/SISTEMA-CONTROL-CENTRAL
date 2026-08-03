# 06_TIME_ENGINE.md

# FACT CENTRAL SaaS

## TIME ENGINE

Versión 1.0

---

# 1. Objetivo

Definir el Motor Oficial de Tiempo de FACT CENTRAL.

El Time Engine será el único responsable de gestionar:

- fechas;
- horas;
- zonas horarias;
- vencimientos;
- recordatorios;
- temporizadores;
- reintentos programados;
- esperas de Workflows;
- SLA;
- calendarios;
- feriados;
- horarios laborales;
- tareas programadas;
- obligaciones periódicas;
- programaciones automáticas del negocio;
- eventos futuros.

Ningún otro módulo podrá crear temporizadores propios.

---

# 2. Principio Fundamental

El tiempo es un recurso compartido.

Todos los módulos deberán solicitar servicios al Time Engine.

Nunca deberán calcular tiempos o mantener temporizadores
por cuenta propia.

---

# 3. Responsabilidades

El Time Engine administrará:

- Scheduler global;
- Jobs;
- Esperas;
- Reintentos;
- Cron;
- SLA;
- Calendarios;
- Horarios;
- Feriados;
- Vencimientos;
- Alarmas;
- Programaciones;
- Obligaciones periódicas;
- Recordatorios;
- Eventos futuros.

---

# 4. Fuente Oficial de Tiempo

Toda la plataforma utilizará:

```text
UTC
```

internamente.

La visualización se convertirá a la zona horaria del Tenant.

---

# 5. Zona Horaria

Cada Tenant tendrá:

- timezone;
- locale;
- formato de fecha;
- formato de hora;
- primer día de semana;
- calendario laboral.

Ejemplo:

```text
America/Lima
```

---

# 6. Entidades

El Time Engine administrará:

- timer;
- schedule;
- calendar;
- holiday;
- working_hours;
- sla;
- reminder;
- retry_policy;
- cron_job;
- timeout;
- deadline;
- recurring_schedule;
- business_obligation;
- business_calendar;
- scheduling_exception.

---

# 7. Estados

Todo temporizador podrá estar en uno de los siguientes estados:

```text
CREATED
SCHEDULED
WAITING
RUNNING
COMPLETED
CANCELLED
EXPIRED
FAILED
RETRYING
ARCHIVED
```

---

# 8. Timer

Cada Timer tendrá:

- timer_id;
- tenant_id;
- workflow_id;
- resource_type;
- resource_id;
- due_at;
- timezone;
- status;
- priority;
- created_at;
- updated_at;
- metadata.

---

# 9. Scheduler

Existirá un Scheduler central.

Nunca deberá existir uno independiente por módulo.

---

# 10. Esperas

Los Workflows utilizarán:

```text
WAIT_TIME
↓
Time Engine
↓
Evento
↓
Workflow continúa
```

---

# 11. Ejemplo

```text
Carga de Voucher
↓
Esperar 3 días
↓
No llega
↓
Crear Alerta
↓
Escalar
```

---

# 12. SLA

Todo SLA tendrá:

- sla_id;
- nombre;
- duración;
- unidad;
- calendario;
- prioridad;
- acciones;
- condiciones;
- escalamiento.

---

# 13. Ejemplos de SLA

```text
Responder alerta:
24 horas

Subir Voucher:
72 horas

Aprobar pago:
48 horas

Registrar ITF:
10 días
```

---

# 14. Calendarios

Cada Tenant podrá tener:

- calendario laboral;
- feriados nacionales;
- feriados propios;
- días no laborables;
- cierres especiales;
- días de contingencia.

---

# 15. Horario Laboral

Ejemplo:

```text
Lunes a viernes

08:00
↓
18:00
```

---

# 16. Feriados

Los SLA podrán:

- ignorar feriados;
- incluir feriados;
- utilizar feriados nacionales;
- utilizar feriados del Tenant.

La configuración dependerá de cada calendario.

---

# 17. Recordatorios

El sistema podrá generar recordatorios mediante:

- correo;
- WhatsApp;
- Push;
- Dashboard;
- SMS;
- bandeja interna.

El envío será realizado por el Notification Engine.

---

# 18. Reintentos

Toda política de reintento tendrá:

- número de intentos;
- intervalo inicial;
- crecimiento del intervalo;
- intervalo máximo;
- errores reintentables;
- errores no reintentables;
- vencimiento.

---

# 19. Backoff

Ejemplo:

```text
1 minuto
5 minutos
15 minutos
1 hora
6 horas
```

---

# 20. Cron

El Time Engine administrará:

- procesos diarios;
- procesos semanales;
- procesos quincenales;
- procesos mensuales;
- procesos trimestrales;
- procesos semestrales;
- procesos anuales;
- procesos personalizados.

---

# 21. Procesos Mensuales

Ejemplos:

- solicitar ITF;
- solicitar PDT;
- solicitar SSCO;
- cerrar producción;
- generar liquidaciones;
- revisar contratos;
- revisar cuentas de pago;
- generar reportes mensuales.

---

# 22. Procesos Quincenales

Ejemplos:

- solicitar TXT SSCO;
- solicitar ITF actualizado;
- seguimiento de Proveedores;
- revisión de pedidos;
- revisión de bancarización;
- revisión de concentración.

---

# 23. Procesos Diarios

Ejemplos:

- respaldos;
- Scrubbing de Storage;
- revisión de DLQ;
- revisión de alertas;
- revisión de Expedientes abiertos;
- revisión de tareas vencidas;
- revisión de Jobs fallidos.

---

# 24. Procesos Horarios

Ejemplos:

- Health Check;
- replicación;
- revisión de colas;
- control de capacidad;
- revisión de Workers;
- validación de sincronización de reloj.

---

# 25. Jobs

Todo Job tendrá:

- job_id;
- tenant_id;
- tipo;
- prioridad;
- estado;
- siguiente ejecución;
- última ejecución;
- resultado;
- retry_count;
- idempotency_key;
- workflow_id;
- resource_id;
- metadata.

---

# 26. Tipos de Job

```text
ONE_TIME
RECURRING
CRON
EVENT_DELAY
WORKFLOW_WAIT
BUSINESS_OBLIGATION
MAINTENANCE
COMPLIANCE
```

---

# 27. Deadline

Todo Workflow podrá definir:

```text
deadline
```

El Time Engine controlará su vencimiento.

---

# 28. Timeout

Todo proceso crítico tendrá timeout.

El timeout deberá ser:

- configurable;
- auditable;
- versionado;
- asociado al tipo de proceso.

---

# 29. Vencimientos

El Time Engine administrará vencimientos relacionados con:

- suscripciones;
- pagos;
- Expedientes;
- documentos;
- contratos;
- cuentas bancarias;
- recordatorios;
- obligaciones;
- SLA;
- periodos de gracia;
- invitaciones;
- sesiones.

---

# 30. Renovaciones

Ejemplo:

```text
Suscripción vence
↓
5 días antes
↓
Primer recordatorio
↓
2 días antes
↓
Segundo aviso
↓
Vence
↓
Grace Period
↓
Suspensión
```

---

# 31. Grace Period

Cada Plan podrá definir un periodo de gracia.

Ejemplos:

```text
0 días
7 días
15 días
30 días
```

---

# 32. Suspensión

Cuando corresponda, el Time Engine emitirá:

```text
subscription.expired
```

El Workflow y Subscription Engine determinarán
las acciones posteriores.

---

# 33. Reactivación

```text
Pago confirmado
↓
subscription.renewed
↓
Reactivar Tenant
```

---

# 34. Integración con Workflow Engine

```text
WAIT_TIME
↓
Timer
↓
Evento
↓
Workflow continúa
```

---

# 35. Integración con Rule Engine

El Rule Engine define:

```text
qué plazo aplicar
```

El Time Engine controla:

```text
cuándo vence
```

---

# 36. Integración con Notification Engine

El Time Engine nunca enviará mensajes directamente.

Generará:

```text
notification.requested
```

---

# 37. Integración con Event Bus

Todos los Timers y Jobs relevantes generarán eventos.

Ejemplos:

```text
timer.created
timer.due
timer.completed
timer.failed
job.started
job.completed
job.failed
sla.breached
business_obligation.overdue
```

---

# 38. Integración con Storage

Ejemplo:

```text
Archivado automático
↓
Timer
↓
Workflow de archivado
```

---

# 39. Integración con SaaS

Ejemplo:

```text
Trial
↓
Expira
↓
Evento
↓
Workflow de conversión o suspensión
```

---

# 40. Integración con Pagos

Ejemplo:

```text
Fecha de pago
↓
Recordatorio
↓
Escalamiento
```

---

# 41. Integración con Expedientes

Ejemplo:

```text
Voucher faltante
↓
72 horas
↓
Alerta
↓
Escalamiento
```

---

# 42. Integración con Auditoría

Toda ejecución registrará:

- inicio;
- fin;
- resultado;
- duración;
- actor;
- Tenant;
- Job;
- Timer;
- recurso;
- motivo.

---

# 43. Prioridades

Los niveles de prioridad serán:

```text
CRITICAL
HIGH
NORMAL
LOW
BACKGROUND
```

---

# 44. Orden de ejecución

Si dos Jobs coinciden:

```text
Mayor prioridad primero
```

Si tienen la misma prioridad,
se utilizará el orden de programación
o la política definida.

---

# 45. Recuperación

Después de una caída:

```text
Leer Timers pendientes
↓
Recalcular estados
↓
Detectar vencidos
↓
Aplicar política
↓
Continuar
```

---

# 46. Persistencia

Los Timers nunca dependerán únicamente de memoria.

Los estados críticos deberán persistirse.

---

# 47. Multi-Tenant

Todo Timer, Job, SLA y calendario pertenecerá a un Tenant,
salvo tareas globales de plataforma.

---

# 48. Horario de Verano

El Time Engine resolverá automáticamente cambios de DST
cuando correspondan a la zona horaria configurada.

---

# 49. Sincronización

Todos los nodos utilizarán una misma referencia temporal confiable.

---

# 50. Precisión

Las fechas críticas utilizarán precisión suficiente
para garantizar orden y auditoría.

La precisión mínima recomendada será de milisegundos.

---

# 51. Drift

El sistema detectará diferencias de reloj entre nodos.

Cuando el desfase supere el límite permitido:

- se generará alerta;
- podrá aislarse el nodo;
- se corregirá la sincronización;
- se auditará el incidente.

---

# 52. Jobs Perdidos

Después de reiniciar:

```text
Buscar Jobs pendientes
↓
Identificar Jobs vencidos
↓
Aplicar política
```

---

# 53. Jobs Duplicados

Un Job no podrá ejecutarse dos veces económicamente.

Podrá ejecutarse más de una vez técnicamente,
pero su efecto deberá ser idempotente.

---

# 54. Idempotencia

Todo Job deberá utilizar una clave de idempotencia.

Ejemplo conceptual:

```text
tenant_id
+
job_type
+
period
+
resource_id
```

---

# 55. Dashboard

El Dashboard temporal podrá mostrar:

- Timers activos;
- Timers vencidos;
- SLA incumplidos;
- Jobs ejecutados;
- Jobs pendientes;
- Jobs fallidos;
- Jobs reintentando;
- obligaciones vencidas.

---

# 56. Métricas

Se medirá:

- tiempo promedio;
- Timers activos;
- reintentos;
- SLA;
- Jobs fallidos;
- Jobs completados;
- Jobs vencidos;
- Jobs duplicados evitados;
- desviación de reloj;
- tiempo de recuperación.

---

# 57. Auditoría

Se registrará:

- job_id;
- timer_id;
- tenant_id;
- actor;
- inicio;
- fin;
- resultado;
- política;
- recurso;
- Workflow;
- Event ID;
- error;
- reintento.

---

# 58. Health

El modelo de salud deberá revisar:

- Scheduler;
- Workers;
- Jobs;
- colas;
- persistencia;
- precisión temporal;
- drift;
- Jobs vencidos;
- Jobs bloqueados.

---

# 59. Pruebas

Deberán realizarse pruebas para:

- cambio de horario;
- caída de nodo;
- Retry;
- Jobs duplicados;
- DST;
- feriados;
- recuperación de Jobs;
- Job vencido durante caída;
- idempotencia;
- múltiples Tenants;
- cambios de zona horaria;
- SLA laborales;
- SLA calendario;
- reprogramación;
- Jobs simultáneos.

---

# 60. Business Scheduling Layer

El Time Engine también será responsable de coordinar
las programaciones automáticas del negocio.

Esta capa no ejecutará directamente la lógica empresarial.

Su responsabilidad será:

- determinar cuándo debe ocurrir algo;
- crear o activar el Job correspondiente;
- emitir el evento;
- despertar el Workflow relacionado;
- solicitar la notificación correspondiente;
- registrar el resultado temporal.

---

# 61. Principio de automatización temporal

Toda obligación periódica del negocio deberá configurarse mediante:

```text
REGLA
+
CALENDARIO
+
JOB
+
WORKFLOW
+
NOTIFICACIÓN
```

Ejemplo:

```text
Regla:
Solicitar TXT SSCO

Calendario:
Día 1 y día 15 de cada mes

Time Engine:
Activa el Job

Workflow Engine:
Genera las tareas correspondientes

Notification Engine:
Envía los avisos
```

---

# 62. Programaciones de cumplimiento

El Time Engine podrá administrar programaciones relacionadas con:

- SSCO;
- ITF;
- PDT;
- contratos;
- cuentas bancarias;
- Expedientes incompletos;
- evidencias faltantes;
- pagos;
- liquidaciones;
- pedidos mensuales;
- alertas tributarias;
- revisiones internas.

---

# 63. Programación SSCO

El sistema podrá programar:

```text
DÍA 1 DE CADA MES
↓
SOLICITAR TXT SSCO ACTUALIZADO

DÍA 15 DE CADA MES
↓
SOLICITAR NUEVA ACTUALIZACIÓN SSCO
```

El Workflow correspondiente podrá:

- crear tarea para Administración o Secretaría;
- solicitar el archivo;
- validar si ya fue cargado;
- evitar tareas duplicadas;
- registrar el periodo;
- generar alerta si no se cumple;
- comparar Proveedores activos;
- actualizar su estado.

---

# 64. Programación ITF

El sistema podrá solicitar mensualmente:

- reporte ITF;
- periodo;
- Proveedor;
- Usuario responsable;
- fecha límite;
- evidencia;
- estado.

Ejemplo:

```text
INICIO DEL MES
↓
CREAR SOLICITUD ITF

FECHA LÍMITE
↓
VERIFICAR ENTREGA

NO ENTREGADO
↓
ALERTA
↓
ESCALAMIENTO
```

---

# 65. Programación PDT

El Time Engine podrá activar la solicitud periódica de:

- PDT mensual;
- constancia de presentación;
- periodo declarado;
- evidencia de pago, cuando corresponda;
- documentación complementaria.

El sistema deberá evitar que una solicitud mensual
modifique o reemplace periodos anteriores.

---

# 66. Programación de contratos

El sistema podrá controlar:

- fecha de inicio;
- fecha de vencimiento;
- renovación;
- recurrencia;
- Cliente;
- Proveedor;
- tipo de servicio;
- alerta previa.

Ejemplo:

```text
CONTRATO VENCE EN 30 DÍAS
↓
PRIMER AVISO

CONTRATO VENCE EN 15 DÍAS
↓
SEGUNDO AVISO

CONTRATO VENCE EN 5 DÍAS
↓
ALERTA CRÍTICA
```

---

# 67. Expedientes abiertos

El sistema podrá revisar Expedientes que lleven:

- demasiados días abiertos;
- documentos faltantes;
- alertas sin resolver;
- tareas vencidas;
- validaciones pendientes.

Ejemplo:

```text
EXPEDIENTE ABIERTO MÁS DE 7 DÍAS
↓
RECORDATORIO

MÁS DE 15 DÍAS
↓
ALERTA

MÁS DE 30 DÍAS
↓
ESCALAMIENTO A ADMINISTRADOR
```

Los plazos serán configurables.

---

# 68. Seguimiento de bancarización

El Time Engine podrá activar revisiones periódicas de:

- porcentaje bancarizado;
- porcentaje no bancarizado;
- desviación frente al objetivo;
- concentración por Proveedor;
- tendencia del periodo;
- saldo pendiente.

Ejemplo:

```text
REVISIÓN DIARIA
↓
CALCULAR AVANCE

DESVIACIÓN MAYOR AL LÍMITE
↓
GENERAR ALERTA

FIN DE QUINCENA
↓
GENERAR INFORME
```

---

# 69. Seguimiento de pedidos

Durante el mes el sistema podrá programar:

- revisión diaria;
- revisión semanal;
- revisión quincenal;
- cierre mensual.

El Workflow podrá evaluar:

- monto asignado;
- monto ejecutado;
- saldo;
- exceso;
- concentración;
- distribución;
- Proveedores sin producción;
- Proveedores sobreutilizados.

---

# 70. Liquidación automática

El Time Engine podrá iniciar el Workflow de liquidación:

```text
FIN DEL PERIODO
↓
CONGELAR PRODUCCIÓN PRELIMINAR
↓
APLICAR REGLAS
↓
GENERAR LIQUIDACIÓN PROVISIONAL
↓
SOLICITAR REVISIÓN
↓
CERRAR
```

La fecha podrá configurarse por Tenant.

Ejemplos:

- último día del mes;
- primer día del mes siguiente;
- cierre manual asistido;
- fecha especial.

---

# 71. Recordatorios de pagos

El sistema podrá programar:

- pago pendiente;
- pago próximo;
- pago vencido;
- Voucher faltante;
- conciliación pendiente;
- pago parcial;
- saldo pendiente.

---

# 72. Cuentas bancarias

El Time Engine podrá controlar:

- próxima revisión;
- vigencia documental;
- cambios recientes;
- confirmación pendiente;
- cuenta desactivada;
- cuenta sin verificar;
- cuenta utilizada en programación cerrada.

---

# 73. Revisiones internas

Podrán programarse:

- auditorías internas;
- verificación de respaldos;
- restauraciones de prueba;
- control de Storage;
- revisión de DLQ;
- revisión de reglas;
- revisión de permisos;
- revisión de sesiones;
- revisión de integraciones;
- revisión de salud;
- revisión de capacidad.

---

# 74. Calendario operativo del Tenant

Cada Tenant podrá tener un calendario operativo con:

- cierres;
- vencimientos;
- solicitudes;
- revisiones;
- liquidaciones;
- pagos;
- auditorías;
- obligaciones.

El Administrador podrá visualizarlo como:

```text
CALENDARIO FACT CENTRAL
```

---

# 75. Plantillas de calendario

FACT CENTRAL podrá ofrecer plantillas como:

## CUMPLIMIENTO MENSUAL

- SSCO día 1;
- SSCO día 15;
- ITF mensual;
- PDT mensual;
- liquidación;
- cierre.

## CONTROL DOCUMENTAL

- Expedientes abiertos;
- documentos faltantes;
- contratos;
- evidencias.

## PAGOS

- preparación;
- aprobación;
- ejecución;
- conciliación.

## INFRAESTRUCTURA

- backups;
- restauraciones;
- Scrubbing;
- revisiones de Storage;
- revisión de DLQ.

---

# 76. Configuración por Tenant

El Administrador podrá configurar:

- día;
- hora;
- frecuencia;
- zona horaria;
- responsables;
- anticipación;
- canales;
- escalamiento;
- prioridad;
- condición de cancelación.

No podrá modificar:

- reglas globales de seguridad;
- aislamiento;
- retenciones obligatorias;
- tareas críticas de plataforma;
- obligaciones protegidas por norma.

---

# 77. Evitar duplicados temporales

Una misma obligación no deberá crear varias tareas iguales.

La clave podrá incluir:

```text
tenant_id
+
schedule_code
+
periodo
+
resource_id
```

Ejemplo:

```text
FC-A7K92M
+
SSCO_UPLOAD
+
2026-08-01
```

---

# 78. Estado de obligación periódica

Cada obligación podrá estar en:

```text
NOT_DUE
UPCOMING
DUE
IN_PROGRESS
COMPLETED
OVERDUE
ESCALATED
WAIVED
CANCELLED
```

---

# 79. Excepción temporal

Una obligación podrá modificarse excepcionalmente por:

- feriado;
- cambio normativo;
- cierre especial;
- indisponibilidad externa;
- autorización administrativa;
- contingencia.

Toda excepción deberá registrar:

- motivo;
- nueva fecha;
- responsable;
- aprobación;
- vigencia;
- auditoría.

---

# 80. Simulación de calendario

Antes de activar una programación,
el Administrador podrá simular:

- Jobs generados;
- Usuarios afectados;
- alertas previstas;
- fechas;
- conflictos;
- carga operativa.

La simulación no generará tareas reales.

---

# 81. Prioridad entre Jobs

Cuando varios Jobs coincidan, se aplicará:

```text
1. Seguridad
2. Cumplimiento legal
3. Integridad documental
4. Pagos
5. Suscripciones
6. Operaciones
7. Reportes
8. Mantenimiento
```

---

# 82. Recuperación de Jobs vencidos

Si el sistema estuvo caído y un Job venció:

```text
REINICIO
↓
DETECTAR JOB VENCIDO
↓
EVALUAR POLÍTICA
```

Resultados posibles:

```text
EXECUTE_IMMEDIATELY
RESCHEDULE
SKIP_WITH_AUDIT
REQUEST_APPROVAL
ESCALATE
```

---

# 83. Notificación de incumplimiento

Cuando una obligación venza sin cumplimiento:

```text
Time Engine
↓
evento overdue
↓
Workflow Engine
↓
crear tarea o escalar
↓
Notification Engine
↓
enviar aviso
```

---

# 84. Métricas operativas

Se medirá:

- obligaciones programadas;
- completadas;
- vencidas;
- escaladas;
- reprogramadas;
- omitidas;
- cumplidas antes de plazo;
- tiempo medio de cumplimiento;
- incumplimientos por Tenant;
- incumplimientos por Usuario;
- incumplimientos por Proveedor.

---

# 85. Dashboard temporal

El Administrador podrá ver:

```text
HOY
PRÓXIMOS 7 DÍAS
ESTE MES
VENCIDOS
ESCALADOS
COMPLETADOS
```

---

# 86. Regla de separación

El Time Engine determina:

```text
CUÁNDO
```

El Rule Engine determina:

```text
QUÉ CORRESPONDE
```

El Workflow Engine determina:

```text
CÓMO SE EJECUTA
```

El Notification Engine determina:

```text
CÓMO SE COMUNICA
```

---

# 87. Integración con NEXUS

El Time Engine podrá interactuar con NEXUS para anticipar
eventos importantes y proponer acciones preventivas.

NEXUS no modificará directamente el calendario
ni ejecutará tareas por sí mismo.

Podrá detectar:

- obligaciones próximas a vencer;
- Proveedores que no presentan ITF;
- Proveedores que no presentan PDT;
- Expedientes abiertos demasiado tiempo;
- contratos próximos a vencer;
- Usuarios con baja producción;
- exceso de concentración;
- desviaciones de bancarización;
- desviaciones del pedido mensual;
- cuentas bancarias sin actualizar;
- acumulación de alertas.

Podrá sugerir:

- adelantar una revisión;
- enviar un recordatorio;
- escalar un caso;
- solicitar documentación;
- redistribuir carga de trabajo;
- generar un informe preventivo.

Las propuestas deberán requerir aprobación cuando impliquen
cambios operativos.

NEXUS nunca podrá:

- modificar calendarios por sí solo;
- cambiar fechas límite;
- eliminar obligaciones;
- cancelar Jobs;
- alterar SLA;
- modificar configuraciones del Tenant;
- omitir obligaciones legales.

---

# 88. Reglas Supremas

## Regla Suprema 1

EL TIEMPO SOLO ES ADMINISTRADO POR EL TIME ENGINE.

## Regla Suprema 2

TODOS LOS MÓDULOS UTILIZAN UTC INTERNAMENTE.

## Regla Suprema 3

NINGÚN WORKFLOW CREA TEMPORIZADORES PROPIOS.

## Regla Suprema 4

TODO TIMER ES PERSISTENTE.

## Regla Suprema 5

LOS SLA SON CONFIGURABLES POR TENANT.

## Regla Suprema 6

LOS RECORDATORIOS SON SOLICITUDES AL NOTIFICATION ENGINE.

## Regla Suprema 7

LOS JOBS SON IDEMPOTENTES.

## Regla Suprema 8

EL REINICIO DE UN NODO NO PUEDE PERDER TEMPORIZADORES.

## Regla Suprema 9

LOS CRON SON ADMINISTRADOS CENTRALMENTE.

## Regla Suprema 10

TODO TIMER ES AUDITABLE.

## Regla Suprema 11

TODA OBLIGACIÓN PERIÓDICA DEL NEGOCIO
SERÁ ADMINISTRADA POR EL TIME ENGINE.

## Regla Suprema 12

EL TIME ENGINE NO EJECUTA DIRECTAMENTE
LA LÓGICA DEL NEGOCIO.

## Regla Suprema 13

LAS PROGRAMACIONES DE SSCO, ITF Y PDT
SERÁN VERSIONADAS POR PERIODO.

## Regla Suprema 14

LOS JOBS VENCIDOS DURANTE UNA CAÍDA
SERÁN RECUPERADOS SEGÚN POLÍTICA.

## Regla Suprema 15

UNA MISMA OBLIGACIÓN NO GENERARÁ
TAREAS DUPLICADAS PARA EL MISMO PERIODO.

## Regla Suprema 16

LOS CALENDARIOS PODRÁN CONFIGURARSE POR TENANT,
SIN DEBILITAR REGLAS SUPERIORES.

## Regla Suprema 17

TODA REPROGRAMACIÓN DEBERÁ SER AUDITABLE.

## Regla Suprema 18

EL CALENDARIO DE NEGOCIO SERÁ UNA FUENTE CENTRAL
PARA VENCIMIENTOS, CIERRES Y OBLIGACIONES.
