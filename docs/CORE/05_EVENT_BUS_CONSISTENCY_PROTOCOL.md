# 05_EVENT_BUS_CONSISTENCY_PROTOCOL.md

# FACT CENTRAL SaaS

## EVENT BUS CONSISTENCY PROTOCOL

Versión 1.0

---

# 1. Objetivo

Definir el protocolo oficial de consistencia del Event Bus de FACT CENTRAL.

Este documento garantiza que todos los eventos del sistema:

- sean persistidos;
- no se pierdan;
- no se procesen dos veces económicamente;
- puedan reintentarse;
- puedan reconstruirse;
- puedan auditarse;
- puedan recuperarse después de una caída.

---

# 2. Principio fundamental

En FACT CENTRAL los eventos representan hechos que ya ocurrieron.

Nunca representan intención.

Ejemplo:

✔ Documento recibido

✔ Pago confirmado

✔ Expediente cerrado

✘ "Tal vez llegue un documento"

---

# 3. Definición de Evento

Todo evento deberá contener:

- event_id
- tenant_id
- aggregate_type
- aggregate_id
- event_type
- event_version
- occurred_at
- producer
- correlation_id
- causation_id
- payload
- metadata
- checksum

---

# 4. Regla Suprema

Todo evento deberá persistirse antes de publicarse.

Nunca:

Aplicación
↓
Publicar evento
↓
Guardar BD

Siempre:

Aplicación
↓
Guardar BD
+
Guardar Outbox
↓
Commit
↓
Publicar

---

# 5. Outbox Pattern

Cada transacción crítica generará:

- modificación de datos
- registro Outbox

en la misma transacción PostgreSQL.

---

# 6. Estados del Evento

CREATED

PERSISTED

READY_TO_PUBLISH

PUBLISHED

ACKNOWLEDGED

FAILED

RETRYING

DEAD_LETTER

ARCHIVED

---

# 7. Flujo Oficial

Acción
↓
Commit PostgreSQL
↓
Evento Outbox
↓
Publisher
↓
Event Bus
↓
Consumer
↓
ACK
↓
Archivado

---

# 8. Tipos de Eventos

Documentales

- document.uploaded
- document.classified
- document.duplicated
- document.validated

Expedientes

- expediente.created
- expediente.completed
- expediente.blocked

Usuarios

- user.created
- manager.created
- membership.approved

Pagos

- payment.generated
- payment.approved
- payment.executed

SaaS

- tenant.created
- subscription.renewed
- subscription.expired

Sistema

- alert.created
- notification.sent
- workflow.completed

---

# 9. Identidad

event_id será globalmente único.

Nunca reutilizable.

---

# 10. Versionado

Todo evento tendrá:

event_type

+

event_version

Ejemplo:

document.uploaded v1

document.uploaded v2

---

# 11. Inmutabilidad

Un evento nunca podrá modificarse.

Si cambia la realidad:

se genera otro evento.

---

# 12. Orden

Dentro del mismo Aggregate deberá mantenerse el orden.

Ejemplo:

Documento

↓

Subido

↓

Clasificado

↓

Validado

↓

Expediente

No podrá invertirse.

---

# 13. Aggregate

Ejemplos:

Document

Expediente

Tenant

Workflow

Pago

Usuario

Proveedor

Cliente

Cada Aggregate mantiene su propia secuencia.

---

# 14. Correlation ID

Relaciona todo un proceso.

Ejemplo:

Subida PDF

↓

OCR

↓

Clasificación

↓

Expediente

↓

Pago

Todos comparten:

correlation_id

---

# 15. Causation ID

Indica qué evento originó otro.

Ejemplo:

document.uploaded

↓

document.classified

↓

expediente.updated

---

# 16. Exactly Once Económico

FACT CENTRAL no necesita exactamente una entrega.

Necesita exactamente un impacto económico.

Por ello:

Puede recibirse un mismo evento dos veces.

Pero:

No puede contabilizarse dos veces.

---

# 17. Idempotencia

Todo Consumer deberá validar:

event_id

+

aggregate_version

+

tenant_id

Si ya fue aplicado:

ignorar.

---

# 18. Consumers

Cada Consumer mantiene:

último evento procesado

offset lógico

checkpoint

estado

fecha

---

# 19. Reintentos

Errores temporales:

Retry.

Errores permanentes:

Dead Letter Queue.

---

# 20. Dead Letter Queue

Cuando un evento supera el máximo de reintentos:

↓

DLQ

↓

Administrador

↓

Reprocesar

o

Descartar justificadamente

Nunca desaparecerá.

---

# 21. Backoff

Ejemplo:

1 s

5 s

30 s

2 min

10 min

30 min

---

# 22. ACK

Un Consumer solo enviará ACK cuando:

la operación haya finalizado correctamente.

---

# 23. NACK

Errores temporales.

Provoca Retry.

---

# 24. Timeout

Todo procesamiento tendrá timeout.

---

# 25. Duplicados

El Event Bus puede entregar dos veces.

La lógica de negocio nunca procesará dos veces.

---

# 26. Persistencia

El Event Bus nunca dependerá solo de RAM.

---

# 27. Recuperación

Si un nodo cae:

Nuevo Worker

↓

Lee Outbox

↓

Continúa publicación

---

# 28. Replay

Debe ser posible reproducir eventos históricos.

Solo lectura.

Nunca para volver a generar pagos.

---

# 29. Replay Seguro

El Replay respetará:

Tenant

Permisos

Versiones

Idempotencia

---

# 30. Multi-Tenant

Todo evento pertenece a:

tenant_id

Nunca se mezclan eventos.

---

# 31. Seguridad

Todo evento deberá registrar:

quién

qué

cuándo

desde dónde

---

# 32. Prioridades

HIGH

NORMAL

LOW

BACKGROUND

---

# 33. Orden Global

No existe.

Solo orden por Aggregate.

---

# 34. Auditoría

Registrar:

event_id

producer

consumer

inicio

fin

duración

resultado

---

# 35. Integración con Workflow

workflow.started

workflow.completed

workflow.failed

---

# 36. Integración con Rule Engine

El Rule Engine puede generar eventos.

Nunca consumirlos directamente para decidir el pasado.

---

# 37. Integración con Notification Engine

Las notificaciones se disparan mediante eventos.

Nunca mediante llamadas directas.

---

# 38. Integración con Upload

upload.received

↓

evento

↓

Workflow

---

# 39. Integración con Storage

storage.available

↓

evento

↓

OCR

---

# 40. Integración con Time Engine

Eventos programados.

---

# 41. Integración con SaaS

tenant.suspended

subscription.expired

trial.finished

---

# 42. Eventos Públicos

Solo ciertos eventos podrán salir mediante API.

---

# 43. Eventos Privados

Nunca abandonan FACT CENTRAL.

---

# 44. Eventos Sensibles

No incluir:

Contraseñas

Tokens

Claves

Datos bancarios completos

---

# 45. Payload

Debe ser pequeño.

Nunca incluir archivos.

Solo referencias.

---

# 46. Eventos de Archivo

Ejemplo:

file_id

tenant_id

hash

storage_key

No el PDF completo.

---

# 47. Event Schema

Todo evento tendrá esquema versionado.

---

# 48. Compatibilidad

Consumidores antiguos podrán seguir funcionando mientras la versión sea compatible.

---

# 49. Métricas

Eventos/min

Errores

Retries

DLQ

Latencia

Consumers activos

---

# 50. Dashboard

Mostrar:

Eventos publicados

Pendientes

DLQ

Retries

Latencia

---

# 51. Observabilidad

Cada evento deberá poder rastrearse de punta a punta.

---

# 52. Health Check

Publisher

Broker

Consumers

Outbox

DLQ

---

# 53. Integridad

Todo evento llevará checksum.

---

# 54. Firma

En eventos críticos podrá utilizarse firma digital interna.

---

# 55. Retención

Los eventos se conservarán según política.

---

# 56. Archivado

Eventos antiguos podrán archivarse.

Nunca modificarse.

---

# 57. Disaster Recovery

Después de una caída:

Reconstruir Outbox

↓

Reanudar publicación

↓

Sin pérdida

---

# 58. Escalabilidad

Millones de eventos.

Miles de Tenants.

Workers paralelos.

---

# 59. Pruebas

Duplicados

Caída Publisher

Caída Consumer

Retry

DLQ

Replay

Orden

---

# 60. Reglas Supremas

## Regla Suprema 1

TODO EVENTO DEBE PERSISTIRSE ANTES DE PUBLICARSE.

## Regla Suprema 2

NINGÚN EVENTO SE MODIFICA.

## Regla Suprema 3

LOS EVENTOS SON HECHOS.

NO INTENCIONES.

## Regla Suprema 4

LOS DUPLICADOS NO DEBEN GENERAR IMPACTO ECONÓMICO.

## Regla Suprema 5

EL ORDEN SOLO ES OBLIGATORIO DENTRO DEL MISMO AGGREGATE.

## Regla Suprema 6

LOS EVENTOS PERTENECEN A UN TENANT.

## Regla Suprema 7

TODO EVENTO DEBE SER AUDITABLE.

## Regla Suprema 8

LOS EVENTOS NUNCA DESAPARECEN SILENCIOSAMENTE.

## Regla Suprema 9

TODO CONSUMER SERÁ IDEMPOTENTE.

## Regla Suprema 10

EL EVENT BUS DEBERÁ PODER RECUPERARSE DESPUÉS DE CUALQUIER CAÍDA SIN PERDER EVENTOS.
