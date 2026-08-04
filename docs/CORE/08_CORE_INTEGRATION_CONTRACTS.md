# 08_CORE_INTEGRATION_CONTRACTS.md

# FACT CENTRAL SaaS

## CORE INTEGRATION CONTRACTS

Versión 1.0

---

# 1. Objetivo

Definir los contratos oficiales de integración entre los motores
centrales de FACT CENTRAL.

Este documento establece:

- dónde termina la responsabilidad de cada motor;
- cómo se comunican;
- qué eventos intercambian;
- qué estados pueden modificar;
- qué datos deben incluir;
- cómo se controla la idempotencia;
- cómo se recuperan después de una caída;
- cómo se conserva el aislamiento multi-tenant;
- cómo se evita duplicar lógica;
- cómo se mantiene la trazabilidad completa.

Los motores integrados son:

- Rule Engine;
- Workflow & Automation Engine;
- Upload State Machine;
- Storage Consistency Protocol;
- Event Bus;
- Time Engine;
- Notification Engine.

---

# 2. Principio fundamental

Cada motor tendrá una responsabilidad exclusiva.

Ningún motor deberá ejecutar funciones que correspondan
oficialmente a otro.

La integración se realizará mediante:

```text
EVENTOS
+
CONTRATOS
+
ESTADOS PERSISTIDOS
+
IDENTIFICADORES DE CORRELACIÓN
+
IDEMPOTENCIA
+
AUDITORÍA
```

---

# 3. Mapa oficial de responsabilidades

## Rule Engine

Determina:

```text
QUÉ CORRESPONDE
```

Evalúa condiciones y genera decisiones.

No ejecuta directamente:

- notificaciones;
- pagos;
- movimientos de Storage;
- eliminación física;
- temporizadores;
- Workflows;
- acciones externas irreversibles.

---

## Workflow Engine

Determina:

```text
CÓMO SE COORDINA
```

Coordina:

- pasos;
- tareas;
- aprobaciones;
- esperas;
- reintentos;
- compensaciones;
- cambios de estado autorizados;
- interacción entre motores.

No decide reglas del negocio.

---

## Upload State Machine

Determina:

```text
CÓMO SE RECIBE EL ARCHIVO
```

Controla:

- sesión;
- transferencia;
- fragmentos;
- integridad;
- seguridad;
- cuarentena;
- recepción confirmada.

No administra:

- almacenamiento definitivo;
- réplicas;
- OCR;
- clasificación;
- Expedientes;
- impacto económico.

---

## Storage Consistency Protocol

Determina:

```text
CÓMO SE PERSISTE Y PROTEGE EL ARCHIVO
```

Controla:

- escritura definitiva;
- promoción;
- versiones;
- réplicas;
- movimientos;
- reparación;
- integridad;
- disponibilidad;
- restauración.

No decide qué representa el documento.

---

## Event Bus

Determina:

```text
CÓMO SE TRANSPORTAN LOS HECHOS
```

Controla:

- persistencia de eventos;
- publicación;
- entrega;
- reintentos;
- ACK;
- DLQ;
- Replay;
- orden por Aggregate;
- trazabilidad.

No ejecuta la lógica de negocio.

---

## Time Engine

Determina:

```text
CUÁNDO DEBE OCURRIR
```

Controla:

- Timers;
- Jobs;
- SLA;
- cron;
- vencimientos;
- obligaciones;
- periodos;
- recuperación temporal.

No ejecuta directamente tareas del negocio.

---

## Notification Engine

Determina:

```text
CÓMO SE COMUNICA
```

Controla:

- destinatarios;
- canales;
- plantillas;
- entrega;
- reintentos;
- confirmación;
- escalamiento;
- preferencias;
- bandeja interna.

No decide si una obligación existe.

---

# 4. Flujo maestro del CORE

```text
EVENTO DE ENTRADA
        ↓
UPLOAD STATE MACHINE
        ↓
RECEIVED_VERIFIED
        ↓
EVENT BUS
        ↓
WORKFLOW ENGINE
        ↓
STORAGE CONSISTENCY
        ↓
AVAILABLE
        ↓
WORKFLOW ENGINE
        ↓
RULE ENGINE
        ↓
DECISIÓN
        ↓
WORKFLOW ENGINE
        ↓
TIME ENGINE / NOTIFICATION ENGINE / OTROS SERVICIOS
        ↓
RESULTADO
        ↓
AUDITORÍA
```

---

# 5. Contrato Upload → Storage

## 5.1 Estado oficial de recepción

El estado:

```text
RECEIVED_VERIFIED
```

significa:

- todos los bytes fueron recibidos;
- el archivo completo fue ensamblado;
- el tamaño fue validado;
- el hash fue calculado;
- el escaneo de seguridad fue aprobado;
- el archivo fue almacenado en cuarentena persistente;
- el registro de ingesta fue confirmado;
- el Tenant fue validado.

No significa todavía:

- almacenamiento definitivo;
- réplica mínima;
- disponibilidad general;
- procesamiento OCR;
- incorporación al Expediente.

---

## 5.2 Evento de entrega

Cuando Upload alcance `RECEIVED_VERIFIED`,
deberá publicar:

```text
upload.received_verified
```

---

## 5.3 Payload mínimo

```text
event_id
tenant_id
ingestion_id
upload_session_id
file_id
temporary_storage_key
file_hash
file_size
mime_type
original_filename
actor_id
active_role
source_channel
occurred_at
correlation_id
causation_id
event_version
```

---

## 5.4 Responsabilidad de Storage

Storage consumirá:

```text
upload.received_verified
```

y creará una operación:

```text
storage.promotion.requested
```

La operación deberá:

1. adquirir lock;
2. copiar desde cuarentena;
3. escribir objeto definitivo;
4. validar tamaño;
5. validar hash;
6. registrar ubicación;
7. generar réplica mínima;
8. marcar ubicación activa;
9. marcar File Object como `AVAILABLE`;
10. publicar evento.

---

## 5.5 Evento final de Storage

Cuando el archivo esté disponible:

```text
storage.file.available
```

---

## 5.6 Significado de AVAILABLE

`AVAILABLE` significa:

- objeto definitivo verificado;
- metadata confirmada;
- ubicación activa;
- política mínima de réplica cumplida;
- lectura autorizada posible;
- procesamiento posterior permitido.

---

## 5.7 Regla de procesamiento

OCR, clasificación y separación documental solo podrán comenzar
después de:

```text
storage.file.available
```

No después de `RECEIVED_VERIFIED`.

---

# 6. Contrato Event Bus → Workflow Engine

## 6.1 Workflow Trigger

Todo Workflow deberá iniciarse o continuar mediante
un Trigger formal.

El Trigger relacionará:

```text
EVENTO
+
FILTROS
+
WORKFLOW
+
ACCIÓN
+
PRIORIDAD
+
VIGENCIA
```

---

## 6.2 Entidad conceptual

```text
workflow_trigger
```

Campos mínimos:

- trigger_id;
- tenant_id;
- event_type;
- event_version;
- event_filter;
- workflow_code;
- workflow_version;
- trigger_action;
- priority;
- status;
- effective_from;
- effective_to;
- created_by;
- approved_by.

---

## 6.3 Acciones de Trigger

```text
START_WORKFLOW
CONTINUE_WORKFLOW
RESUME_WORKFLOW
CANCEL_WORKFLOW
ESCALATE_WORKFLOW
START_SUBWORKFLOW
```

---

## 6.4 Ejemplo

```text
Evento:
upload.received.verified

Workflow:
STORAGE_PROMOTION

Acción:
START_WORKFLOW
```

---

## 6.5 Ejemplo de continuación

```text
Evento:
timer.due

Workflow:
EXPEDIENT_DOCUMENT_WAIT

Acción:
CONTINUE_WORKFLOW
```

---

## 6.6 Evento sin Trigger

Si un evento no tiene Trigger:

- no se eliminará;
- se marcará como no procesado por Workflow;
- permanecerá auditable;
- podrá ser utilizado por otro Consumer;
- podrá generar alerta si era obligatorio.

---

# 7. Contrato Rule Engine → Workflow Engine

## 7.1 Evaluación

El Workflow enviará contexto al Rule Engine.

Ejemplo:

```text
¿Puede cerrarse el Expediente?
```

---

## 7.2 Respuesta del Rule Engine

La respuesta deberá contener:

- evaluation_id;
- tenant_id;
- rule_id;
- rule_code;
- rule_version;
- result;
- severity;
- reason;
- requirements;
- recommended_actions;
- blocking;
- evaluated_at;
- correlation_id.

---

## 7.3 Resultados permitidos

```text
ALLOW
DENY
REQUIRE
WARN
ALERT
CLASSIFY
CALCULATE
ASSIGN
REQUEST_APPROVAL
RECOMMEND
HOLD
UNKNOWN
ERROR
```

---

## 7.4 Regla de ejecución

El Rule Engine no enviará notificaciones directamente.

Publicará:

```text
rule.evaluated
```

El Workflow interpretará el resultado.

---

## 7.5 Ejemplo de ALERT

```text
rule.evaluated

rule_code:
COMPLIANCE.SSCO.SUPPLIER_BLOCK

result:
ALERT

severity:
CRITICAL

blocking:
true
```

El Workflow podrá:

- bloquear asignaciones;
- crear tarea;
- solicitar notificación;
- escalar;
- esperar revisión.

---

## 7.6 UNKNOWN

Cuando el resultado sea:

```text
UNKNOWN
```

el Workflow deberá:

- no asumir cumplimiento;
- crear tarea de revisión;
- solicitar dato faltante;
- mantener el recurso en estado seguro;
- impedir cierre automático cuando sea crítico.

---

## 7.7 ERROR

Cuando el resultado sea:

```text
ERROR
```

el Workflow deberá:

- no continuar con una acción crítica;
- registrar error;
- reintentar si corresponde;
- enviar a revisión;
- conservar contexto.

---

# 8. Contrato Workflow → Notification Engine

## 8.1 Solicitud

El Workflow solicitará una notificación mediante:

```text
notification.requested
```

---

## 8.2 Payload mínimo

```text
notification_request_id
tenant_id
workflow_id
resource_type
resource_id
notification_type
severity
priority
recipient_scope
required_permissions
template_code
template_version
data_reference
requested_channels
scheduled_at
expires_at
acknowledgement_required
correlation_id
causation_id
idempotency_key
```

---

## 8.3 Responsabilidad de Notification Engine

Notification Engine deberá:

1. validar Tenant;
2. resolver destinatarios;
3. validar permisos;
4. aplicar restricciones de información;
5. aplicar preferencias;
6. seleccionar canales;
7. construir mensajes;
8. enviar;
9. reintentar;
10. registrar entrega;
11. escalar si corresponde.

---

## 8.4 Confirmación

Cuando una notificación requiera confirmación,
Notification Engine publicará:

```text
notification.acknowledged
```

o:

```text
notification.acknowledgement.expired
```

El Workflow podrá continuar según el resultado.

---

# 9. Resolución oficial de destinatarios

## 9.1 Entrada

La resolución utilizará:

- tenant_id;
- notification_type;
- resource_type;
- resource_id;
- severity;
- responsible_user_id;
- responsible_manager_id;
- owner_id;
- escalation_level;
- recipient_scope.

---

## 9.2 Algoritmo

```text
1. Consultar regla vigente de destinatarios.
2. Resolver relaciones del recurso.
3. Aplicar severidad.
4. Aplicar escalamiento.
5. Validar permisos.
6. Eliminar destinatarios sin relación.
7. Aplicar preferencias.
8. Conservar canales obligatorios.
9. Crear lista final.
```

---

## 9.3 Reglas predeterminadas

### CRITICAL

```text
Administrador del Tenant
+
responsable directo
+
Usuario relacionado
```

### HIGH

```text
responsable directo
+
Usuario relacionado
```

### MEDIUM

```text
responsable directo
```

### LOW

```text
bandeja interna del responsable
```

Estas reglas podrán configurarse sin eliminar
los destinatarios obligatorios.

---

# 10. Contrato Workflow → Time Engine

## 10.1 Solicitud de espera

El Workflow solicitará:

```text
timer.requested
```

---

## 10.2 Payload mínimo

```text
timer_id
tenant_id
workflow_id
workflow_execution_id
step_id
resource_type
resource_id
due_at
timezone
timer_type
priority
recovery_policy
correlation_id
idempotency_key
```

---

## 10.3 Evento de vencimiento

Cuando llegue la fecha:

```text
timer.due
```

---

## 10.4 Workflow de continuación

El Trigger deberá relacionar:

```text
timer.due
→
CONTINUE_WORKFLOW
```

---

## 10.5 Cancelación

Si el Workflow recibe antes el dato esperado:

```text
timer.cancel.requested
```

Time Engine deberá cancelar el Timer de forma idempotente.

---

# 11. Contrato Time Engine → Notification Engine

Time Engine no enviará mensajes.

Cuando una obligación venza, publicará:

```text
business_obligation.overdue
```

Workflow Engine decidirá la reacción.

Posteriormente podrá publicar:

```text
notification.requested
```

---

# 12. Contrato Workflow → Storage

Workflow Engine no ejecutará operaciones físicas.

Solicitará:

```text
storage.operation.requested
```

---

## 12.1 Operaciones permitidas

```text
PROMOTE
REPLICATE
MOVE
REPAIR
RESTORE
ARCHIVE
DELETE_LOGICAL
REQUEST_PHYSICAL_DELETION
```

---

## 12.2 Payload mínimo

```text
operation_id
tenant_id
file_id
file_version_id
operation_type
source_location
target_policy
priority
requested_by
workflow_id
correlation_id
idempotency_key
```

---

## 12.3 Eventos de respuesta

```text
storage.operation.started
storage.operation.completed
storage.operation.failed
storage.file.available
storage.file.degraded
storage.file.corrupted
storage.file.repaired
```

---

# 13. Contrato Storage → Workflow Engine

Workflow Engine podrá esperar:

```text
storage.operation.completed
```

o:

```text
storage.file.available
```

Si recibe:

```text
storage.operation.failed
```

deberá:

- evaluar si el error es reintentable;
- crear Retry;
- enviar a DLQ cuando corresponda;
- crear tarea humana;
- escalar si afecta integridad.

---

# 14. Contrato Event Bus → Consumers

## 14.1 Datos obligatorios

Todo evento deberá contener:

- event_id;
- tenant_id;
- event_type;
- event_version;
- aggregate_type;
- aggregate_id;
- aggregate_version;
- occurred_at;
- producer;
- correlation_id;
- causation_id;
- payload;
- metadata;
- checksum.

---

## 14.2 Regla de orden

No existe orden global.

El orden deberá conservarse para:

```text
tenant_id
+
aggregate_id
```

---

## 14.3 Partition Key conceptual

```text
hash(
    tenant_id
    +
    aggregate_id
)
```

La tecnología concreta podrá variar.

---

## 14.4 Regla de Consumer

Todo Consumer deberá:

1. validar Tenant;
2. validar versión;
3. comprobar idempotencia;
4. iniciar transacción;
5. aplicar operación;
6. registrar evento procesado;
7. confirmar transacción;
8. enviar ACK.

---

# 15. Registro de eventos procesados

Cada Consumer deberá conservar un registro persistente.

Entidad conceptual:

```text
processed_event
```

Campos mínimos:

- processed_event_id;
- tenant_id;
- event_id;
- consumer_name;
- aggregate_id;
- aggregate_version;
- processed_at;
- result;
- status;
- correlation_id.

Restricción obligatoria:

```text
UNIQUE (
    tenant_id,
    event_id,
    consumer_name
)
```

---

# 16. Exactly Once económico

FACT CENTRAL aceptará entrega técnica:

```text
AT LEAST ONCE
```

pero exigirá impacto económico:

```text
EXACTLY ONCE
```

Esto se logrará mediante:

- Consumers idempotentes;
- restricciones únicas;
- registro de eventos procesados;
- transacciones;
- identificadores económicos únicos;
- periodos cerrados;
- validaciones de estado.

---

# 17. Diferencia entre duplicados

## Intento repetido

Misma solicitud reenviada.

Control:

```text
idempotency_key
```

## Archivo físico duplicado

Mismo contenido.

Control:

```text
file_hash
```

## Documento lógico duplicado

Misma identidad documental.

Control:

```text
logical_document_key
```

## CPE fiscal duplicado

Mismo:

```text
RUC emisor
+
tipo CPE
+
serie
+
correlativo
```

## Evento repetido

Mismo:

```text
event_id
+
consumer
```

## Efecto económico duplicado

Misma operación económica.

Control:

```text
economic_operation_id
```

---

# 18. Captura de versiones

Toda ejecución deberá capturar al inicio:

- workflow_version;
- rule_versions;
- configuration_version;
- template_version;
- schema_version;
- jurisdiction_rule_version.

---

## 18.1 Cambio durante ejecución

Si una Regla cambia mientras un Workflow está activo:

```text
EL WORKFLOW CONTINÚA CON LA VERSIÓN CAPTURADA
```

salvo:

- migración autorizada;
- emergencia de seguridad;
- obligación legal inmediata;
- corrección crítica aprobada.

Toda migración deberá auditarse.

---

# 19. Contrato de recuperación

Todos los motores deberán persistir:

- estado;
- último checkpoint;
- heartbeat;
- propietario del trabajo;
- último evento;
- próximo paso;
- reintentos;
- error;
- idempotency_key;
- correlation_id.

---

# 20. Recuperación de Workflow

Cuando un Worker se caiga:

```text
1. Detectar heartbeat vencido.
2. Leer último estado persistido.
3. Comprobar evento esperado.
4. Comprobar Timer asociado.
5. Comprobar paso ejecutado.
6. Comprobar idempotencia.
7. Reanudar desde el último checkpoint seguro.
```

---

# 21. Recuperación de Storage

Cuando una operación quede incompleta:

```text
1. Verificar lock.
2. Verificar origen.
3. Verificar destino.
4. Validar hash.
5. Consultar estado persistido.
6. Continuar o compensar.
7. No eliminar origen hasta confirmar destino.
```

---

# 22. Recuperación de Timers

Después de una caída:

```text
1. Buscar Timers pendientes.
2. Identificar Timers vencidos.
3. Aplicar recovery_policy.
4. Publicar timer.due cuando corresponda.
5. Evitar duplicados.
6. Registrar ejecución tardía.
```

---

# 23. Recuperación de Notificaciones

Después de una caída:

```text
1. Buscar notificaciones QUEUED, PROCESSING o RETRYING.
2. Consultar proveedor cuando sea posible.
3. Verificar idempotencia.
4. Reenviar si corresponde.
5. Mantener bandeja interna.
6. Registrar resultado.
```

---

# 24. Estado del Tenant durante Workflows

Antes de ejecutar cada paso sensible,
se deberá comprobar el estado del Tenant.

## ACTIVE

Operación normal.

## GRACE_PERIOD

Aplicar límites configurados.

## READ_ONLY

Solo pasos de consulta, descarga, pago SaaS y recuperación permitida.

## SUSPENDED

No iniciar nuevas operaciones empresariales.

Los Workflows ya iniciados deberán:

- pausarse si son operativos;
- continuar si protegen integridad;
- continuar si corresponden a seguridad;
- continuar si corresponden a Billing SaaS;
- continuar si corresponden a recuperación;
- registrar la decisión.

---

# 25. Workflows permitidos durante suspensión

Podrán continuar:

- recuperación;
- reparación de Storage;
- backups;
- seguridad;
- auditoría;
- exportación autorizada;
- Billing SaaS;
- reactivación;
- conservación.

No deberán continuar normalmente:

- nuevas cargas;
- nuevas asignaciones;
- nuevas liquidaciones;
- nuevos pagos ERP;
- nuevas operaciones comerciales.

---

# 26. Dead Letter Queue

La DLQ podrá ser físicamente compartida,
pero deberá estar aislada lógicamente por:

```text
tenant_id
```

No se creará obligatoriamente una cola física por Tenant.

---

## 26.1 Campos mínimos

- dead_letter_id;
- tenant_id;
- event_id;
- consumer_name;
- event_type;
- payload_reference;
- error_code;
- error_message;
- attempts;
- first_failed_at;
- last_failed_at;
- status;
- resolution;
- resolved_by.

---

## 26.2 Acceso

### Administrador del Tenant

Podrá ver eventos operativos de su Tenant
cuando la interfaz lo permita.

### Superadmin

Podrá revisar fallos técnicos globales.

### Secretaría, Usuario y Gestor

No accederán directamente a la DLQ técnica.

---

## 26.3 Reprocesamiento

El reprocesamiento deberá:

- mantener el mismo event_id;
- utilizar un nuevo reprocess_id;
- validar idempotencia;
- limitarse al Tenant;
- registrar responsable;
- registrar motivo;
- impedir efectos económicos duplicados.

---

# 27. Locks de integración

Los locks críticos deberán estar aislados por:

```text
tenant_id
+
resource_id
+
operation_type
```

Ejemplo:

```text
FC-A7K92M
+
FILE-001
+
MOVE
```

La implementación podrá utilizar PostgreSQL
u otro coordinador durable aprobado.

No se permitirá depender solo de memoria local.

---

# 28. Contrato de seguridad

Toda llamada, evento o tarea deberá validar:

- tenant_id;
- identidad;
- servicio técnico;
- permiso;
- alcance;
- recurso;
- estado;
- sensibilidad;
- versión;
- firma o autenticidad cuando corresponda.

---

# 29. Datos sensibles

Los eventos no deberán contener:

- contraseñas;
- CVV;
- claves privadas;
- tokens completos;
- cuentas bancarias completas;
- documentos completos;
- archivos binarios.

Se utilizarán referencias seguras.

---

# 30. Contrato de auditoría

Toda interacción entre motores deberá registrar:

- tenant_id;
- source_engine;
- target_engine;
- event_id;
- workflow_id;
- resource_id;
- action;
- state_before;
- state_after;
- occurred_at;
- processed_at;
- actor;
- service_identity;
- result;
- error;
- correlation_id;
- causation_id.

---

# 31. Catálogo mínimo de eventos del CORE

## Upload

```text
upload.session.created
upload.started
upload.paused
upload.completed
upload.integrity.validated
upload.security.validated
upload.received.verified
upload.duplicate.detected
upload.conflict.detected
upload.rejected
upload.recovered
```

---

## Storage

```text
storage.operation.requested
storage.operation.started
storage.operation.completed
storage.operation.failed
storage.file.available
storage.file.degraded
storage.file.corrupted
storage.file.repaired
storage.file.restored
```

---

## Rule Engine

```text
rule.evaluation.requested
rule.evaluated
rule.conflict.detected
rule.exception.requested
rule.exception.approved
rule.exception.rejected
```

---

## Workflow

```text
workflow.started
workflow.step.started
workflow.step.completed
workflow.waiting
workflow.resumed
workflow.blocked
workflow.failed
workflow.completed
workflow.cancelled
workflow.compensating
workflow.compensated
```

---

## Time Engine

```text
timer.requested
timer.created
timer.cancel.requested
timer.cancelled
timer.due
timer.completed
timer.failed
job.started
job.completed
job.failed
sla.breached
business.obligation.due
business.obligation.overdue
```

---

## Notification Engine

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

# 32. Convención de nombres

Los eventos deberán expresarse en pasado
cuando representen hechos.

Ejemplos correctos:

```text
upload.received.verified
storage.file.available
workflow.completed
notification.sent
```

Las solicitudes podrán utilizar:

```text
requested
```

Ejemplos:

```text
storage.operation.requested
notification.requested
timer.requested
```

---

# 33. Contrato de error

Todo error técnico deberá incluir:

- error_code;
- error_category;
- retryable;
- severity;
- message;
- engine;
- resource_id;
- tenant_id;
- occurred_at;
- correlation_id.

---

# 34. Categorías de error

```text
VALIDATION
SECURITY
PERMISSION
TENANT_STATE
TRANSIENT
TIMEOUT
CONFLICT
INTEGRITY
EXTERNAL_PROVIDER
DATA_UNKNOWN
INTERNAL
```

---

# 35. Política de Retry

## TRANSIENT

Reintentar.

## TIMEOUT

Reintentar con límite.

## EXTERNAL_PROVIDER

Reintentar según adaptador.

## VALIDATION

No reintentar sin corrección.

## SECURITY

No reintentar automáticamente.

## PERMISSION

No reintentar automáticamente.

## CONFLICT

Requiere resolución.

## INTEGRITY

Bloquear y revisar.

---

# 36. Backoff común

Los motores podrán utilizar:

```text
Intento 1:
inmediato

Intento 2:
30 segundos

Intento 3:
2 minutos

Intento 4:
10 minutos

Intento 5:
30 minutos
```

Las políticas específicas podrán variar.

---

# 37. Límite de responsabilidad del Event Bus

Event Bus:

- transporta;
- persiste;
- reintenta;
- entrega;
- conserva orden por Aggregate.

No:

- decide;
- valida reglas del negocio;
- modifica pagos;
- resuelve destinatarios;
- mueve archivos;
- ejecuta Workflows.

---

# 38. Límite de responsabilidad del Workflow

Workflow Engine:

- coordina;
- espera;
- reintenta;
- escala;
- compensa.

No:

- ejecuta código arbitrario;
- sustituye Rule Engine;
- almacena archivos;
- envía mensajes directamente;
- controla reloj propio;
- procesa pagos directamente sin servicios especializados.

---

# 39. Límite de responsabilidad del Rule Engine

Rule Engine:

- evalúa;
- decide;
- explica.

No:

- orquesta pasos;
- envía notificaciones;
- crea Timers directamente;
- mueve Storage;
- ejecuta pagos;
- elimina información.

---

# 40. Límite de responsabilidad del Time Engine

Time Engine:

- programa;
- vence;
- activa Jobs;
- publica eventos temporales.

No:

- decide qué documento es obligatorio;
- genera liquidaciones directamente;
- envía mensajes;
- mueve archivos;
- cambia reglas.

---

# 41. Límite de responsabilidad de Notification Engine

Notification Engine:

- comunica;
- registra;
- reintenta;
- confirma;
- escala.

No:

- decide obligaciones;
- concede permisos;
- modifica Expedientes;
- ejecuta pagos;
- cambia estados económicos.

---

# 42. Límite de responsabilidad de Upload

Upload:

- recibe;
- valida transferencia;
- verifica integridad inicial;
- escanea seguridad;
- conserva cuarentena.

No:

- confirma disponibilidad final;
- crea impacto económico;
- clasifica fiscalmente;
- crea liquidaciones;
- mueve réplicas.

---

# 43. Límite de responsabilidad de Storage

Storage:

- protege el objeto;
- replica;
- mueve;
- repara;
- restaura.

No:

- interpreta CPE;
- determina Cliente;
- determina Proveedor;
- decide bancarización;
- crea pagos.

---

# 44. Matriz de integración

| Origen | Destino | Contrato principal |
|---|---|---|
| Upload | Event Bus | `upload.received.verified` |
| Event Bus | Workflow | Trigger por evento |
| Workflow | Storage | `storage.operation.requested` |
| Storage | Event Bus | `storage.file.available` |
| Event Bus | Workflow | Continuar procesamiento |
| Workflow | Rule Engine | Evaluación con contexto |
| Rule Engine | Event Bus | `rule.evaluated` |
| Event Bus | Workflow | Aplicar decisión |
| Workflow | Time Engine | `timer.requested` |
| Time Engine | Event Bus | `timer.due` |
| Event Bus | Workflow | Continuar o escalar |
| Workflow | Notification | `notification.requested` |
| Notification | Event Bus | estados de entrega |
| Event Bus | Workflow | ACK o expiración |

---

# 45. Escenario completo: Voucher faltante

```text
Factura disponible
↓
workflow.document_processing
↓
Rule Engine evalúa
↓
rule.evaluated:
REQUIRE VOUCHER
↓
Workflow marca Expediente incompleto
↓
timer.requested:
72 horas
↓
notification.requested:
Usuario + Gestor
↓
Notification Engine envía
↓
Voucher llega antes del plazo
↓
timer.cancel.requested
↓
Workflow reevalúa
↓
Rule Engine:
ALLOW
↓
Workflow continúa
```

---

# 46. Escenario completo: SSCO

```text
Archivo TXT SSCO cargado
↓
Storage AVAILABLE
↓
Workflow procesa
↓
Proveedor detectado
↓
Rule Engine:
ALERT CRITICAL
+
HOLD
↓
Workflow bloquea nuevas asignaciones
↓
notification.requested
↓
Administrador y responsable reciben alerta
↓
Workflow crea tarea de revisión
```

---

# 47. Escenario completo: caída durante Storage

```text
Storage MOVE iniciado
↓
Worker cae
↓
Heartbeat vence
↓
Recovery Worker detecta operación
↓
Verifica origen
↓
Verifica destino
↓
Verifica hash
↓
Continúa desde checkpoint
↓
storage.operation.completed
```

---

# 48. Escenario completo: evento duplicado

```text
event_id EV-100
↓
Consumer procesa
↓
Registra processed_event
↓
Falla ACK
↓
Event Bus reentrega EV-100
↓
Consumer consulta processed_event
↓
Detecta duplicado
↓
No repite efecto
↓
ACK
```

---

# 49. Escenario completo: regla cambia durante Workflow

```text
Workflow inicia
↓
captura Rule Version 3
↓
Administración activa Rule Version 4
↓
Workflow continúa con Version 3
↓
Nuevos Workflows usan Version 4
```

---

# 50. Pruebas obligatorias de integración

Deberán probarse:

- Upload → Storage;
- Storage → Workflow;
- Workflow → Rule;
- Rule → Workflow;
- Workflow → Time;
- Time → Workflow;
- Workflow → Notification;
- Notification → Workflow;
- Event Bus duplicado;
- evento fuera de orden;
- Tenant suspendido;
- Rule Version modificada;
- Workflow recuperado;
- Storage recuperado;
- Timer vencido durante caída;
- Notification ACK perdido;
- DLQ aislada por Tenant;
- Worker con Tenant incorrecto.

---

# 51. Reglas supremas

## Regla Suprema 1

CADA MOTOR TENDRÁ UNA RESPONSABILIDAD EXCLUSIVA.

## Regla Suprema 2

NINGÚN MOTOR EJECUTARÁ DIRECTAMENTE
FUNCIONES QUE PERTENECEN A OTRO.

## Regla Suprema 3

UPLOAD TERMINA SU RESPONSABILIDAD
EN RECEIVED_VERIFIED.

## Regla Suprema 4

STORAGE CONFIRMA DISPONIBILIDAD
MEDIANTE AVAILABLE.

## Regla Suprema 5

OCR Y CLASIFICACIÓN SOLO COMIENZAN
DESPUÉS DE STORAGE.FILE.AVAILABLE.

## Regla Suprema 6

EL RULE ENGINE DECIDE.

## Regla Suprema 7

EL WORKFLOW ENGINE COORDINA.

## Regla Suprema 8

EL TIME ENGINE DETERMINA CUÁNDO.

## Regla Suprema 9

EL NOTIFICATION ENGINE COMUNICA.

## Regla Suprema 10

EL EVENT BUS TRANSPORTA HECHOS.

## Regla Suprema 11

TODO EVENTO TENDRÁ TENANT_ID,
EVENT_ID Y CORRELATION_ID.

## Regla Suprema 12

TODO CONSUMER SERÁ IDEMPOTENTE.

## Regla Suprema 13

LOS EVENTOS DUPLICADOS NO GENERARÁN
EFECTOS ECONÓMICOS DUPLICADOS.

## Regla Suprema 14

TODA EJECUCIÓN CAPTURARÁ
LAS VERSIONES UTILIZADAS.

## Regla Suprema 15

LOS WORKFLOWS ACTIVOS NO CAMBIARÁN
SILENCIOSAMENTE DE REGLA.

## Regla Suprema 16

TODO ESTADO CRÍTICO SERÁ PERSISTENTE.

## Regla Suprema 17

LA CAÍDA DE UN NODO NO DEBERÁ
PERDER PROCESOS NI DOCUMENTOS.

## Regla Suprema 18

LA DLQ PODRÁ SER COMPARTIDA FÍSICAMENTE,
PERO ESTARÁ AISLADA POR TENANT.

## Regla Suprema 19

LOS LOCKS NO DEPENDERÁN
EXCLUSIVAMENTE DE MEMORIA LOCAL.

## Regla Suprema 20

TODA INTEGRACIÓN SERÁ AUDITABLE.

## Regla Suprema 21

NINGÚN ARCHIVO SERÁ CONSIDERADO
DISPONIBLE ANTES DE STORAGE AVAILABLE.

## Regla Suprema 22

NINGUNA NOTIFICACIÓN DEFINIRÁ
POR SÍ MISMA UNA OBLIGACIÓN.

## Regla Suprema 23

NINGÚN TIMER EJECUTARÁ
DIRECTAMENTE LA LÓGICA DEL NEGOCIO.

## Regla Suprema 24

TODO TRIGGER DE WORKFLOW
SERÁ EXPLÍCITO, VERSIONADO Y AUDITABLE.
