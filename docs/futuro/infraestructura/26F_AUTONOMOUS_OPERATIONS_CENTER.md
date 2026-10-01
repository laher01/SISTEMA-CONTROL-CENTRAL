# 26F — AUTONOMOUS OPERATIONS CENTER

# FACT CENTRAL

## Centro Oficial de Operaciones Autónomas de NEXUS

**Versión:** 2.0
**Estado:** Arquitectura lógica consolidada
**Modelo:** Supervisión autónoma con gobierno administrativo

---

# 1. Objetivo

Definir el Centro de Operaciones Autónomas de FACT CENTRAL encargado de coordinar la supervisión, análisis, recomendación y ejecución controlada de acciones operativas sobre la infraestructura.

El Autonomous Operations Center, denominado **AOC**, funcionará como capa coordinadora entre:

* System Health;
* Capacity Planning;
* Infrastructure Topology;
* Disaster Recovery;
* Cost Model;
* Resource Engine;
* Executive Intelligence;
* NEXUS;
* Administración.

Su función principal será transformar información técnica en decisiones operativas seguras.

---

# 2. Principio fundamental

> NEXUS PODRÁ OPERAR AUTÓNOMAMENTE DENTRO DE POLÍTICAS PREVIAMENTE AUTORIZADAS, PERO ADMINISTRACIÓN CONSERVARÁ EL CONTROL SOBRE LAS DECISIONES CRÍTICAS.

La autonomía no significará ausencia de control.

Significará:

```text
OBSERVAR
↓
ENTENDER
↓
PREDECIR
↓
DECIDIR
↓
AUTORIZAR CUANDO CORRESPONDA
↓
EJECUTAR
↓
VERIFICAR
↓
APRENDER
```

---

# 3. Función del AOC

El AOC deberá responder permanentemente cinco preguntas:

```text
1. ¿Qué está ocurriendo?

2. ¿Por qué está ocurriendo?

3. ¿Qué puede ocurrir después?

4. ¿Qué debemos hacer?

5. ¿Funcionó la acción ejecutada?
```

---

# 4. Arquitectura conceptual

```text
                    FACT CENTRAL
                         │
                         ▼
                     TELEMETRY
                         │
                         ▼
                  SYSTEM HEALTH
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      CAPACITY        COST MODEL     RECOVERY
      PLANNING
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                   NEXUS ANALYSIS
                         │
                         ▼
             AUTONOMOUS OPERATIONS
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
            AUTO      APPROVAL    MANUAL
              │          │          │
              └──────────┼──────────┘
                         ▼
                    ORCHESTRATOR
                         │
                         ▼
                       ACTION
                         │
                         ▼
                      VERIFY
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
            SUCCESS              FAILURE
               │                   │
               ▼                   ▼
            RECORD              ROLLBACK
                                   │
                                   ▼
                                ESCALATE
```

---

# 5. Fuentes de información

El AOC deberá recibir información de:

* nodos;
* APIs;
* PostgreSQL;
* Storage Manager;
* Storage Pools;
* Queue;
* Event Bus;
* workers;
* OCR;
* IA;
* red;
* Cloudflare;
* backups;
* réplicas;
* integraciones externas;
* costos;
* utilización;
* proyecciones;
* auditoría.

---

# 6. Operational State

El AOC deberá mantener un estado operacional global.

Estados posibles:

```text
NORMAL
OBSERVATION
DEGRADED
HIGH_RISK
CRITICAL
RECOVERY
SAFE_MODE
MAINTENANCE
```

---

# 7. Clasificación de decisiones

Toda acción se clasificará como:

```text
AUTO
APPROVAL_REQUIRED
MANUAL_ONLY
```

Esta clasificación será obligatoria.

---

# 8. AUTO

Acciones de bajo riesgo y reversibles podrán ejecutarse automáticamente.

Ejemplos:

* reiniciar worker;
* reintentar trabajo;
* redistribuir job;
* retirar temporalmente nodo no saludable del balanceo;
* activar worker disponible;
* aplicar backpressure;
* ejecutar health check adicional.

Toda acción deberá registrarse.

---

# 9. APPROVAL_REQUIRED

Acciones con impacto relevante requerirán aprobación administrativa.

Ejemplos:

* agregar infraestructura con costo;
* ampliar almacenamiento;
* promover determinada réplica;
* modificar límites importantes;
* activar recursos de emergencia;
* ejecutar restauraciones;
* cambiar políticas de capacidad.

---

# 10. MANUAL_ONLY

Determinadas operaciones deberán permanecer exclusivamente bajo control humano.

Ejemplos:

* eliminar backups;
* destruir datos;
* eliminar auditoría;
* modificar controles fundamentales de seguridad;
* ejecutar acciones irreversibles de alto impacto.

---

# 11. Policy Engine

NEXUS deberá disponer de políticas configurables.

Ejemplo:

```text
worker_restart:
AUTO

node_isolation:
AUTO

scale_workers:
AUTO_WITH_LIMIT

add_paid_vps:
APPROVAL_REQUIRED

restore_database:
APPROVAL_REQUIRED

delete_backup:
MANUAL_ONLY
```

Las políticas no deberán estar dispersas como condiciones rígidas por todo el código.

---

# 12. Límites de autonomía

Administración podrá definir:

```text
Máximo de workers automáticos
Máximo de nodos automáticos
Presupuesto automático
Capacidad máxima
Storage permitido
Tiempo máximo de ejecución
```

---

# 13. Ejemplo de límite

```text
Workers autorizados:
20

Workers actuales:
16

NEXUS necesita:
+3

Resultado:
AUTO
```

Pero:

```text
NEXUS necesita:
+10

Total:
26

Resultado:
APPROVAL_REQUIRED
```

---

# 14. Autonomía económica

Las acciones automáticas deberán respetar el presupuesto definido en:

`26D_INFRASTRUCTURE_COST_MODEL.md`

Ejemplo:

```text
Presupuesto automático:
S/ 500

Costo acción:
S/ 120

AUTO
```

Si:

```text
Costo:
S/ 900
```

entonces:

```text
APPROVAL_REQUIRED
```

---

# 15. Capacity Automation

El AOC recibirá señales de:

`26C_CAPACITY_PLANNING.md`

Ejemplo:

```text
CPU sostenido:
87 %

Queue:
creciendo

Workers:
saturados
```

Capacity Manager podrá recomendar:

```text
ACTIVATE 4 WORKERS
```

AOC evaluará política y ejecutará o solicitará autorización.

---

# 16. Escalamiento predictivo

NEXUS no deberá depender únicamente de alcanzar un límite.

Ejemplo:

```text
Carga actual:
68 %

Proyección en 2 horas:
91 %
```

AOC podrá preparar capacidad antes del pico.

---

# 17. Scale Up

Podrá significar:

* aumentar workers;
* activar nodos;
* aumentar recursos;
* habilitar procesamiento adicional;
* incorporar almacenamiento autorizado.

---

# 18. Scale Down

Cuando disminuya la carga:

```text
CPU:
12 %

Queue:
0

Workers:
20
```

NEXUS podrá recomendar o ejecutar:

```text
20 → 8 workers
```

reduciendo consumo y costos.

---

# 19. Cooldown

El escalamiento deberá utilizar períodos de estabilización.

No deberá ocurrir:

```text
SCALE UP
↓
SCALE DOWN
↓
SCALE UP
↓
SCALE DOWN
```

cada pocos segundos.

---

# 20. Hysteresis

Los umbrales de aumento y reducción podrán ser diferentes.

Ejemplo:

```text
Scale Up:
>80 %

Scale Down:
<40 %
```

Esto evitará oscilaciones.

---

# 21. Node Automation

AOC podrá gestionar estados:

```text
ACTIVE
DRAINING
MAINTENANCE
OFFLINE
RECOVERING
```

---

# 22. Retirada segura de nodo

Nunca deberá apagarse un nodo con trabajos activos sin tratamiento.

Flujo:

```text
ACTIVE
↓
DRAINING
↓
NO NEW JOBS
↓
ACTIVE JOBS FINISH
↓
0 JOBS
↓
OFFLINE
```

---

# 23. Node Failure

Si:

```text
NODE-02
OFFLINE
```

AOC podrá:

1. confirmar pérdida de heartbeat;
2. ejecutar health check;
3. marcar nodo;
4. liberar trabajos recuperables;
5. redistribuir;
6. verificar capacidad restante;
7. escalar si es necesario;
8. generar incidente.

---

# 24. Storage Automation

AOC deberá trabajar con Storage Manager.

Ejemplo:

```text
STORAGE A:
84 %

STORAGE B:
42 %
```

Podrá recomendar:

```text
REDIRECT NEW WRITES
+
REBALANCE
```

---

# 25. Expansión de Storage

Si NEXUS predice:

```text
90 % en 30 días
```

AOC deberá generar:

```text
STORAGE EXPANSION RECOMMENDATION
```

incluyendo:

* capacidad recomendada;
* costo;
* tiempo estimado;
* riesgo de no actuar.

---

# 26. Nuevo dispositivo

Cuando aparezca un nuevo SSD/NAS/Storage:

```text
DETECTED
↓
HEALTH CHECK
↓
SECURITY CHECK
↓
ADMIN APPROVAL
↓
STORAGE POOL
```

No deberá incorporarse automáticamente un dispositivo desconocido a datos críticos.

---

# 27. Database Operations

AOC deberá observar:

* PostgreSQL Primary;
* réplicas;
* replication lag;
* conexiones;
* locks;
* latencia;
* capacidad.

---

# 28. Database Failover

Ante caída del Primary:

```text
PRIMARY FAILED
↓
VERIFY
↓
SELECT VALID REPLICA
↓
POLICY CHECK
↓
PROMOTE
↓
VERIFY
↓
RESUME
```

La automatización exacta dependerá de la política y madurez de la infraestructura.

---

# 29. Integridad antes que disponibilidad

Si existe duda entre:

```text
CONTINUAR RÁPIDO
```

y

```text
PROTEGER INTEGRIDAD
```

NEXUS deberá priorizar integridad.

---

# 30. Safe Mode

Ante riesgo grave:

```text
NORMAL
↓
INTEGRITY RISK
↓
SAFE_MODE
```

Safe Mode podrá:

* bloquear determinadas escrituras;
* detener procesamiento;
* mantener lectura;
* conservar uploads;
* aislar componentes;
* solicitar intervención.

---

# 31. Queue Operations

AOC deberá observar:

```text
queue depth
growth
job age
failure rate
workers
```

Si aumenta la cola:

```text
QUEUE BACKLOG
↓
CAUSE ANALYSIS
```

No deberá aumentar workers automáticamente si el verdadero problema es PostgreSQL o Storage.

---

# 32. Root Cause First

Ejemplo:

```text
Queue ↑
Processing ↓
```

podría deberse a:

```text
CPU
Storage
Database
External API
Worker
Network
```

AOC deberá intentar identificar la causa antes de actuar.

---

# 33. Backpressure

Cuando el sistema esté saturado podrá:

* reducir tareas secundarias;
* limitar operaciones no críticas;
* retrasar procesos pesados;
* priorizar adquisición;
* proteger servicios esenciales.

---

# 34. Prioridades operativas

### PRIORIDAD 1

* seguridad;
* autenticación;
* integridad;
* adquisición documental;
* durable storage.

### PRIORIDAD 2

* base de datos;
* expedientes;
* procesamiento esencial.

### PRIORIDAD 3

* OCR;
* clasificación;
* integraciones.

### PRIORIDAD 4

* reportes;
* analítica;
* aprendizaje;
* procesos secundarios.

---

# 35. Load Shedding

En condiciones extremas, tareas de baja prioridad podrán suspenderse temporalmente.

Ejemplo:

```text
CRITICAL LOAD
↓
PAUSE ANALYTICS
PAUSE HISTORICAL REPORTS
PAUSE LEARNING
```

sin detener adquisición documental.

---

# 36. Disaster Recovery Activation

AOC se integrará con:

`26B_DISASTER_RECOVERY_PLAN.md`

Cuando un incidente alcance determinada severidad:

```text
INCIDENT
↓
CLASSIFICATION
↓
DR POLICY
↓
RECOVERY WORKFLOW
```

---

# 37. Recuperación automática

Ejemplos permitidos por política:

* reiniciar servicio;
* reasignar job;
* retirar nodo;
* activar réplica secundaria;
* reconstruir worker.

---

# 38. Recuperación administrada

Ejemplos:

```text
RESTORE DATABASE
RESTORE HISTORICAL BACKUP
FULL SITE FAILOVER
```

deberán normalmente requerir autorización.

---

# 39. Emergency Policy

Administración podrá definir acciones previamente aprobadas para emergencias.

Ejemplo:

```text
Si:
Primary Storage perdido
+
Replica válida disponible

Entonces:
activar réplica automáticamente
```

---

# 40. Ventana de autorización

Una solicitud podrá tener:

```text
CREATED
↓
WAITING_ADMIN
```

con:

```text
approval_deadline
```

---

# 41. Autorización por vencimiento

Solo determinadas acciones técnicas previamente autorizadas podrán ejecutarse al vencer el plazo.

Ejemplo:

```text
Capacidad crítica
+
acción reversible
+
dentro de presupuesto
+
política autoriza timeout
```

Entonces:

```text
AUTO_APPROVED_BY_POLICY
```

---

# 42. Restricción de timeout

El vencimiento nunca deberá autorizar automáticamente:

* privilegios administrativos;
* eliminación de información;
* cambios de seguridad críticos;
* destrucción de backups;
* acciones irreversibles.

---

# 43. Approval Center

Ruta propuesta:

**Administración → NEXUS → Centro de Aprobaciones**

Podrá mostrar:

```text
Acción
Motivo
Urgencia
Costo
Riesgo
Beneficio
Tiempo límite
Recomendación
```

---

# 44. Opciones administrativas

Ejemplo:

```text
[ APROBAR ]
[ RECHAZAR ]
[ MODIFICAR ]
[ POSPONER ]
```

---

# 45. Explicabilidad

Toda recomendación deberá explicar:

```text
QUÉ
POR QUÉ
IMPACTO
RIESGO
COSTO
ALTERNATIVAS
```

NEXUS no deberá limitarse a:

> "Se recomienda escalar."

---

# 46. Ejemplo

```text
RECOMENDACIÓN NEXUS

Acción:
Activar NODE-04.

Motivo:
Queue crece 18 % por hora.

Capacidad actual:
86 %.

Proyección:
95 % en 47 minutos.

Costo:
Sin costo adicional.
Nodo propio disponible.

Riesgo:
Bajo.

[ APROBAR ]
```

---

# 47. Action Plan

Antes de ejecutar una acción compleja deberá generarse un plan.

```text
ACTION PLAN

1. Validate Node
2. Drain affected service
3. Activate Node
4. Redistribute
5. Verify
6. Close incident
```

---

# 48. Precondition Check

Antes de ejecutar:

```text
PRECONDITIONS
```

deberán verificarse.

Ejemplo:

```text
Replica healthy?
YES

Backup current?
YES

Capacity available?
YES
```

---

# 49. Ejecución

Toda acción deberá tener:

```text
action_id
policy_id
initiator
timestamp
parameters
status
```

---

# 50. Estados de acción

```text
PROPOSED
WAITING_APPROVAL
APPROVED
EXECUTING
VERIFYING
SUCCESS
FAILED
ROLLBACK
CANCELLED
```

---

# 51. Post-Action Verification

Una acción no deberá considerarse exitosa únicamente porque el comando terminó.

Ejemplo:

```text
START NODE
↓
COMMAND SUCCESS
↓
HEALTH CHECK
↓
READINESS
↓
TRAFFIC TEST
↓
SUCCESS
```

---

# 52. Rollback

Las acciones reversibles deberán disponer de rollback cuando sea técnicamente posible.

```text
ACTION
↓
FAILURE
↓
ROLLBACK
↓
VERIFY
```

---

# 53. Rollback imposible

Si una acción no puede revertirse:

```text
NON_REVERSIBLE
```

deberá tener una clasificación de riesgo superior y normalmente requerirá autorización.

---

# 54. Verification Window

Después de determinados cambios, NEXUS deberá observar el sistema durante un periodo.

Ejemplo:

```text
Scale workers
↓
Observe 10 min
↓
Queue improving?
CPU stable?
Errors stable?
```

---

# 55. Acción ineficaz

Si:

```text
ACTION SUCCESS
```

pero:

```text
PROBLEM CONTINUES
```

NEXUS deberá clasificarla:

```text
TECHNICALLY_SUCCESSFUL
OPERATIONALLY_INEFFECTIVE
```

y continuar el análisis.

---

# 56. Incident Manager

Cada problema significativo deberá crear:

```text
incident_id
severity
status
root_cause
affected_components
actions
timeline
owner
```

---

# 57. Estados de incidente

```text
DETECTED
INVESTIGATING
MITIGATING
RECOVERING
MONITORING
RESOLVED
CLOSED
```

---

# 58. Correlación

Múltiples alertas podrán pertenecer a un mismo incidente.

```text
Storage latency
Queue backlog
OCR slowdown
API latency
```

pueden derivarse de:

```text
STORAGE NODE FAILURE
```

---

# 59. Evitar acciones contradictorias

El AOC deberá impedir:

```text
Agent A:
ADD NODE

Agent B:
REMOVE NODE
```

simultáneamente sobre el mismo problema.

Las operaciones deberán coordinarse.

---

# 60. Operational Lock

Acciones críticas podrán utilizar bloqueos operativos.

Ejemplo:

```text
storage-rebalance-lock
database-failover-lock
capacity-change-lock
```

---

# 61. Command Queue

Las acciones del AOC deberán pasar por una cola controlada.

```text
DECISION
↓
COMMAND QUEUE
↓
ORCHESTRATOR
↓
EXECUTION
```

Esto permitirá auditoría y recuperación.

---

# 62. Priority Commands

Las órdenes tendrán prioridades:

```text
EMERGENCY
CRITICAL
HIGH
NORMAL
LOW
```

---

# 63. Cost-Aware Operations

Antes de escalar, NEXUS podrá comparar:

```text
OPCIÓN A
Activar VPS

OPCIÓN B
Activar PC disponible

OPCIÓN C
Reducir procesos secundarios
```

y evaluar:

```text
Costo
Rendimiento
Riesgo
Tiempo
```

---

# 64. Resource-Aware Operations

El AOC consultará:

`15_RESOURCE_ENGINE.md`

para conocer recursos disponibles antes de contratar o activar nuevos.

---

# 65. Ejemplo

```text
Necesidad:
+8 workers

Recursos:

VPS-01:
sin capacidad

PC-02:
capacidad para 3

PC-03:
capacidad para 5

Resultado:
usar PC-02 + PC-03
```

sin contratar infraestructura adicional.

---

# 66. Predictive Operations

NEXUS podrá actuar utilizando proyecciones.

Ejemplo:

```text
Viernes 17:00

Histórico:
pico de +180 %

Predicción:
nuevo pico probable

Acción:
preactivar capacidad
```

---

# 67. Scheduled Capacity

Cuando existan patrones conocidos, podrá prepararse infraestructura antes del pico y reducirse posteriormente.

---

# 68. Cloudflare Coordination

El AOC podrá utilizar telemetría del Edge para distinguir:

```text
LEGITIMATE_SPIKE
SUSPICIOUS_TRAFFIC
ATTACK
```

La respuesta será diferente en cada caso.

---

# 69. Pico legítimo

Si miles de gestores autenticados cargan documentos:

```text
LEGITIMATE_SPIKE
```

la primera respuesta deberá ser escalar y administrar capacidad, no bloquear indiscriminadamente.

---

# 70. Ataque

Si se detecta tráfico malicioso:

```text
ATTACK
```

la respuesta podrá incluir:

* rate limiting;
* bloqueo;
* challenge;
* aislamiento;
* protección adicional.

---

# 71. Estado desconocido

Si no existe suficiente evidencia:

```text
UNKNOWN
```

NEXUS deberá aplicar políticas conservadoras y recopilar más señales.

---

# 72. External Service Operations

Si SUNAT, OpenAI, correo u otro proveedor falla:

```text
SERVICE DEGRADED
↓
CIRCUIT BREAKER
↓
QUEUE JOBS
↓
WAIT
↓
RETRY
```

No deberán perderse trabajos.

---

# 73. Multi-Provider Strategy

Cuando resulte necesario, determinadas funciones podrán disponer de proveedor alternativo.

Ejemplo conceptual:

```text
OCR PROVIDER A
↓ failure
OCR PROVIDER B
```

La decisión deberá considerar costo y calidad.

---

# 74. Notifications

El AOC deberá poder enviar alertas por canales configurados.

Ejemplos:

* panel;
* correo;
* notificación;
* WhatsApp cuando exista integración autorizada.

---

# 75. Escalamiento humano

Si un incidente no puede resolverse automáticamente:

```text
ESCALATE_TO_ADMIN
```

La alerta deberá explicar el problema y no limitarse a un código técnico.

---

# 76. Dashboard AOC

Ruta propuesta:

**Administración → NEXUS → Centro de Operaciones**

Deberá mostrar:

```text
System Health
Incidentes
Acciones activas
Aprobaciones
Capacity
Nodes
Storage
Queue
Costs
Recovery
Predicciones
```

---

# 77. Vista general

Ejemplo:

```text
NEXUS OPERATIONS CENTER

SYSTEM HEALTH       94
CAPACITY            71 %
RECOVERY READINESS  98
COST EFFICIENCY     87

ACTIVE INCIDENTS     1
PENDING APPROVALS    2
AUTOMATIC ACTIONS    3
```

---

# 78. Live Operations

El Administrador podrá observar:

```text
NODE-03 ACTIVATING
Storage Rebalance 34 %
Queue Recovery 81 %
Backup Running
```

---

# 79. Kill Switch

Administración deberá disponer de capacidad para detener determinadas automatizaciones.

Ejemplo:

```text
[ PAUSE AUTONOMOUS OPERATIONS ]
```

Esto no deberá apagar necesariamente FACT CENTRAL.

Detendrá las acciones autónomas configuradas.

---

# 80. Automation Scope

Podrá pausarse únicamente un ámbito:

```text
Scaling
Storage
Recovery
Cost Optimization
```

sin detener otros.

---

# 81. Emergency Stop

Acciones automáticas peligrosamente anormales deberán poder detenerse inmediatamente.

---

# 82. Auditoría total

Toda acción deberá responder:

```text
Quién
Qué
Cuándo
Por qué
Qué política
Qué datos utilizó
Qué ejecutó
Qué ocurrió
```

---

# 83. Decision Record

Ejemplo:

```text
decision_id
incident_id
policy_id
recommendation
confidence
risk
cost
decision
approver
timestamp
```

---

# 84. Confidence Score

Las recomendaciones podrán incluir confianza:

```text
0–100
```

Una baja confianza podrá elevar el requisito de intervención humana.

---

# 85. Risk Score

Cada acción podrá tener:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 86. Matriz autonomía-riesgo

Ejemplo:

```text
LOW + REVERSIBLE
→ AUTO

MEDIUM + REVERSIBLE
→ AUTO / POLICY

HIGH
→ APPROVAL_REQUIRED

CRITICAL / IRREVERSIBLE
→ MANUAL_ONLY
```

---

# 87. Learning Loop

Después de cada acción:

```text
PROBLEM
↓
DECISION
↓
ACTION
↓
RESULT
↓
LEARNING
```

NEXUS podrá mejorar recomendaciones futuras.

---

# 88. Restricción de aprendizaje

El aprendizaje no deberá modificar silenciosamente políticas críticas de seguridad o autorización.

Las políticas críticas deberán continuar bajo gobierno administrativo.

---

# 89. Simulation Mode

El AOC deberá permitir:

```text
SIMULATION
```

En este modo NEXUS podrá decir:

> Habría activado NODE-03.

sin ejecutar realmente la acción.

---

# 90. Shadow Mode

Antes de habilitar automatización completa podrá utilizarse:

```text
SHADOW MODE
```

NEXUS tomará decisiones y registrará qué habría hecho.

Administración podrá comparar esas decisiones con las humanas.

---

# 91. Etapas de autonomía

Se recomienda evolucionar:

```text
LEVEL 0
Monitoring

LEVEL 1
Recommendations

LEVEL 2
Human Approval

LEVEL 3
Limited Automation

LEVEL 4
Policy-Governed Automation
```

FACT CENTRAL no deberá comenzar directamente con autonomía máxima.

---

# 92. Nivel 0

NEXUS observa.

No actúa.

---

# 93. Nivel 1

NEXUS recomienda.

Administrador ejecuta.

---

# 94. Nivel 2

NEXUS prepara la acción.

Administrador aprueba.

NEXUS ejecuta.

---

# 95. Nivel 3

Acciones de bajo riesgo son automáticas.

Las demás requieren aprobación.

---

# 96. Nivel 4

Operaciones habituales funcionan autónomamente dentro de políticas, límites económicos y controles de seguridad.

Administración mantiene supervisión.

---

# 97. No existir autonomía ilimitada

> NEXUS NUNCA DEBERÁ TENER AUTORIDAD ILIMITADA SOBRE INFRAESTRUCTURA, SEGURIDAD O DATOS.

---

# 98. Integración con Infrastructure Topology

`26A_INFRASTRUCTURE_TOPOLOGY.md`

responde:

> ¿QUÉ RECURSOS EXISTEN?

AOC puede actuar sobre esos recursos.

---

# 99. Integración con Disaster Recovery

`26B_DISASTER_RECOVERY_PLAN.md`

responde:

> ¿QUÉ HACEMOS CUANDO FALLAN?

AOC coordina la ejecución.

---

# 100. Integración con Capacity Planning

`26C_CAPACITY_PLANNING.md`

responde:

> ¿CUÁNTA CAPACIDAD NECESITAMOS?

AOC coordina el escalamiento.

---

# 101. Integración con Cost Model

`26D_INFRASTRUCTURE_COST_MODEL.md`

responde:

> ¿CUÁNTO CUESTA?

AOC utiliza esa información antes de decidir.

---

# 102. Integración con System Health

`26E_SYSTEM_HEALTH_MODEL.md`

responde:

> ¿CÓMO ESTÁ EL SISTEMA?

AOC utiliza esas señales para actuar.

---

# 103. Ciclo operacional completo

```text
SYSTEM HEALTH
      ↓
DETECTION
      ↓
ROOT CAUSE ANALYSIS
      ↓
CAPACITY / RECOVERY NEED
      ↓
RESOURCE ANALYSIS
      ↓
COST ANALYSIS
      ↓
RISK ANALYSIS
      ↓
POLICY ENGINE
      ↓
AUTO / APPROVAL / MANUAL
      ↓
ORCHESTRATOR
      ↓
EXECUTION
      ↓
VERIFICATION
      ↓
AUDIT
      ↓
LEARNING
```

---

# 104. Regla Suprema de autonomía

> NEXUS DEBERÁ TENER LA AUTONOMÍA SUFICIENTE PARA PROTEGER Y MANTENER FACT CENTRAL, PERO NUNCA TANTA AUTONOMÍA COMO PARA ELIMINAR EL CONTROL DEL ADMINISTRADOR SOBRE DECISIONES CRÍTICAS.

---

# 105. Regla Suprema de integridad

> ANTE CONFLICTO ENTRE DISPONIBILIDAD, VELOCIDAD, COSTO E INTEGRIDAD, LA INTEGRIDAD DE LOS DATOS TENDRÁ PRIORIDAD.

---

# 106. Regla Suprema de ejecución

> NINGUNA ACCIÓN AUTÓNOMA SE CONSIDERARÁ EXITOSA HASTA QUE SU RESULTADO HAYA SIDO VERIFICADO.

---

# 107. Regla Suprema de trazabilidad

> TODA DECISIÓN Y TODA ACCIÓN DE NEXUS DEBERÁ PODER SER EXPLICADA Y AUDITADA POSTERIORMENTE.

---

# 108. Estado del documento

**AUTONOMOUS OPERATIONS CENTER — ARQUITECTURA LÓGICA DEFINIDA**

El nivel real de autonomía deberá habilitarse progresivamente durante implementación.

FACT CENTRAL comenzará con observabilidad, recomendaciones y aprobación humana.

Las funciones autónomas deberán habilitarse posteriormente mediante pruebas, simulación, Shadow Mode, límites operativos, políticas administrativas y validación de seguridad.
