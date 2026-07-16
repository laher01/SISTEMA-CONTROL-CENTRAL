# 18_ENGINE_INTERFACES.md

# FACT CENTRAL

## Interfaces entre Motores de NEXUS

---

# Objetivo

Definir los contratos de comunicación entre los motores de NEXUS.

Cada motor deberá conocer exactamente:

- qué información recibe;
- qué información devuelve;
- qué eventos publica;
- qué eventos escucha;
- qué permisos requiere;
- qué errores puede generar.

Este documento será el puente entre la arquitectura y la implementación del backend.

---

# Principio General

Ningún motor accederá directamente a otro motor.

Toda comunicación se realizará mediante:

- eventos;
- APIs internas;
- contratos de datos;
- colas;
- mensajes versionados.

---

# Contrato Base

Toda solicitud interna deberá incluir:

- request_id;
- correlation_id;
- organizacion_id;
- usuario_id;
- gestor_id, cuando corresponda;
- expediente_id, cuando corresponda;
- documento_id, cuando corresponda;
- motor_origen;
- fecha_hora;
- prioridad;
- payload;
- versión del contrato.

Toda respuesta deberá incluir:

- request_id;
- correlation_id;
- motor_responsable;
- estado;
- resultado;
- errores;
- advertencias;
- nivel de confianza;
- fecha_hora;
- duración;
- versión del contrato.

---

# Estados de Respuesta

- SUCCESS
- PARTIAL_SUCCESS
- PENDING
- REQUIRES_REVIEW
- REJECTED
- FAILED
- RETRY_SCHEDULED
- CANCELLED

---

# Memory System

## Recibe

- solicitudes de memoria;
- correcciones;
- resúmenes;
- eventos históricos;
- datos de aprendizaje.

## Devuelve

- memoria relevante;
- historial;
- resúmenes;
- versiones anteriores;
- nivel de confianza.

## Publica

- MEMORY_UPDATED
- MEMORY_CONFLICT_DETECTED
- MEMORY_SUMMARY_CREATED

## Escucha

- DOCUMENT_PROCESSED
- EXPEDIENT_UPDATED
- DECISION_COMPLETED
- LEARNING_APPROVED

---

# Knowledge Graph

## Recibe

- entidades;
- relaciones;
- evidencias;
- correcciones;
- confianza.

## Devuelve

- relaciones;
- subgrafos;
- conexiones;
- rutas de conocimiento;
- entidades relacionadas.

## Publica

- RELATION_CREATED
- RELATION_UPDATED
- RELATION_CONFLICT
- KNOWLEDGE_GRAPH_UPDATED

## Escucha

- COMPANY_CREATED
- DOCUMENT_RELATED
- EXPEDIENT_UPDATED
- LEARNING_APPROVED

---

# State Engine

## Recibe

- cambios de estado;
- eventos;
- estados de agentes;
- estados de misiones;
- estados del sistema.

## Devuelve

- estado actual;
- bloqueos;
- alertas;
- entidades activas;
- salud del sistema.

## Publica

- STATE_CHANGED
- BLOCKAGE_DETECTED
- SYSTEM_OVERLOAD
- STATE_INCONSISTENCY

## Escucha

- todos los eventos de cambio de estado.

---

# Event Bus

## Recibe

- eventos válidos.

## Devuelve

- confirmación de publicación;
- identificador del evento;
- estado de entrega.

## Publica

- EVENT_PUBLISHED
- EVENT_DELIVERED
- EVENT_FAILED

## Escucha

- no aplica.

---

# Event Router

## Recibe

- eventos desde el Event Bus.

## Devuelve

- destinatarios;
- prioridad;
- ruta;
- cola;
- reglas aplicadas.

## Publica

- EVENT_ROUTED
- EVENT_REJECTED
- EVENT_DUPLICATE_DETECTED
- EVENT_ESCALATED

## Escucha

- todos los eventos publicados.

---

# Scheduler

## Recibe

- tareas;
- fecha de ejecución;
- prioridad;
- dependencias;
- política de reintentos.

## Devuelve

- programación;
- fecha estimada;
- cola asignada;
- estado.

## Publica

- TASK_SCHEDULED
- TASK_STARTED
- TASK_DELAYED
- TASK_EXPIRED
- TASK_CANCELLED

## Escucha

- EVENT_ROUTED
- MISSION_CREATED
- RETRY_REQUESTED

---

# Context Engine

## Recibe

- usuario;
- permisos;
- tarea;
- expediente;
- documento;
- misión;
- período;
- reglas aplicables.

## Devuelve

- paquete de contexto;
- fuentes;
- restricciones;
- nivel de confianza;
- fecha de expiración.

## Publica

- CONTEXT_CREATED
- CONTEXT_UPDATED
- CONTEXT_CONFLICT
- CONTEXT_EXPIRED

## Escucha

- STATE_CHANGED
- MEMORY_UPDATED
- KNOWLEDGE_GRAPH_UPDATED
- PERMISSION_CHANGED

---

# Reasoning Engine

## Recibe

- contexto;
- reglas;
- evidencias;
- historial;
- estado;
- objetivos.

## Devuelve

- conclusiones;
- hipótesis;
- alternativas;
- conflictos;
- nivel de confianza;
- explicación.

## Publica

- REASONING_COMPLETED
- HYPOTHESIS_CREATED
- CONFLICT_DETECTED
- HUMAN_REVIEW_REQUIRED

## Escucha

- CONTEXT_CREATED
- CONTEXT_UPDATED
- MISSION_REQUIRES_REASONING

---

# Decision Engine

## Recibe

- razonamiento;
- alternativas;
- riesgos;
- permisos;
- reglas;
- objetivos.

## Devuelve

- decisión;
- nivel de autorización;
- justificación;
- alternativa seleccionada;
- acciones requeridas.

## Publica

- DECISION_CREATED
- DECISION_APPROVED
- DECISION_REJECTED
- DECISION_REQUIRES_HUMAN

## Escucha

- REASONING_COMPLETED
- HUMAN_VALIDATION_RECEIVED

---

# Action Planner

## Recibe

- decisión;
- objetivo;
- contexto;
- recursos;
- dependencias;
- restricciones.

## Devuelve

- plan de acción;
- tareas;
- responsables;
- cronograma;
- dependencias;
- riesgos.

## Publica

- ACTION_PLAN_CREATED
- ACTION_PLAN_UPDATED
- REPLANNING_REQUIRED

## Escucha

- DECISION_APPROVED
- CONTEXT_UPDATED
- EXECUTION_FAILED

---

# Execution Engine

## Recibe

- plan de acción;
- tareas;
- agentes asignados;
- recursos;
- prioridad.

## Devuelve

- resultados;
- estados;
- errores;
- métricas;
- evidencias de ejecución.

## Publica

- EXECUTION_STARTED
- ACTION_COMPLETED
- ACTION_FAILED
- EXECUTION_COMPLETED
- EXECUTION_RECOVERY_REQUIRED

## Escucha

- ACTION_PLAN_CREATED
- TASK_STARTED
- RETRY_APPROVED

---

# Operational Quality Engine

## Recibe

- resultados de ejecución;
- reglas;
- evidencias;
- métricas;
- expectativas.

## Devuelve

- aprobación;
- observaciones;
- rechazo;
- nivel de calidad;
- recomendaciones.

## Publica

- QUALITY_APPROVED
- QUALITY_OBSERVED
- QUALITY_REJECTED
- REPROCESS_REQUIRED

## Escucha

- EXECUTION_COMPLETED
- ACTION_COMPLETED

---

# Continuous Learning System

## Recibe

- resultados validados;
- correcciones;
- decisiones;
- errores;
- patrones;
- retroalimentación humana.

## Devuelve

- aprendizajes;
- mejoras;
- conocimiento actualizado;
- nuevas reglas sugeridas;
- confianza.

## Publica

- LEARNING_PROPOSED
- LEARNING_APPROVED
- LEARNING_REJECTED
- MODEL_UPDATE_RECOMMENDED

## Escucha

- QUALITY_APPROVED
- HUMAN_CORRECTION
- DECISION_CORRECTED

---

# Goal Engine

## Recibe

- objetivos;
- indicadores;
- contexto estratégico;
- prioridades;
- resultados.

## Devuelve

- objetivos activos;
- avance;
- desviaciones;
- nuevos objetivos sugeridos.

## Publica

- GOAL_CREATED
- GOAL_UPDATED
- GOAL_COMPLETED
- GOAL_AT_RISK

## Escucha

- EXECUTIVE_RECOMMENDATION
- STRATEGY_RESULT
- MISSION_COMPLETED

---

# Strategy Engine

## Recibe

- objetivos;
- recursos;
- contexto;
- riesgos;
- indicadores;
- historial.

## Devuelve

- estrategias;
- alternativas;
- simulaciones;
- estrategia seleccionada.

## Publica

- STRATEGY_PROPOSED
- STRATEGY_APPROVED
- STRATEGY_UPDATED
- STRATEGY_FAILED

## Escucha

- GOAL_CREATED
- GOAL_AT_RISK
- CONTEXT_CHANGED

---

# Priority Engine

## Recibe

- objetivos;
- estrategias;
- misiones;
- riesgos;
- plazos;
- montos;
- recursos.

## Devuelve

- prioridad calculada;
- justificación;
- orden de atención;
- cambios de prioridad.

## Publica

- PRIORITY_ASSIGNED
- PRIORITY_CHANGED
- CRITICAL_PRIORITY_DETECTED

## Escucha

- GOAL_UPDATED
- STRATEGY_APPROVED
- STATE_CHANGED
- RISK_DETECTED

---

# Resource Engine

## Recibe

- solicitudes de recursos;
- prioridad;
- carga;
- costo;
- disponibilidad;
- restricciones.

## Devuelve

- recursos asignados;
- capacidad disponible;
- costo estimado;
- alternativas.

## Publica

- RESOURCE_ASSIGNED
- RESOURCE_RELEASED
- RESOURCE_OVERLOADED
- RESOURCE_UNAVAILABLE

## Escucha

- ACTION_PLAN_CREATED
- PRIORITY_CHANGED
- SYSTEM_OVERLOAD

---

# Orchestration Engine

## Recibe

- objetivos;
- estrategias;
- prioridades;
- recursos;
- misiones;
- eventos;
- estados.

## Devuelve

- coordinación;
- asignación global;
- secuencia operativa;
- resolución de conflictos;
- estado general.

## Publica

- ORCHESTRATION_STARTED
- ORCHESTRATION_UPDATED
- CONFLICT_RESOLVED
- ORCHESTRATION_FAILED

## Escucha

- GOAL_CREATED
- STRATEGY_APPROVED
- PRIORITY_ASSIGNED
- RESOURCE_ASSIGNED
- MISSION_CREATED

---

# Executive Intelligence Engine

## Recibe

- indicadores;
- resultados;
- riesgos;
- objetivos;
- estrategias;
- recursos;
- estado global;
- gemelo digital.

## Devuelve

- recomendaciones ejecutivas;
- proyecciones;
- alertas;
- oportunidades;
- simulaciones.

## Publica

- EXECUTIVE_RECOMMENDATION
- STRATEGIC_RISK_DETECTED
- BUSINESS_OPPORTUNITY_DETECTED

## Escucha

- GOAL_COMPLETED
- STRATEGY_RESULT
- QUALITY_APPROVED
- DASHBOARD_UPDATED

---

# Reglas de Compatibilidad

Todo contrato deberá tener versión.

Ejemplo:

```text
engine_interface_version: 1.0
event_schema_version: 1.0
