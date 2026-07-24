# 26E — SYSTEM HEALTH MODEL

# FACT CENTRAL

## Modelo Oficial de Salud del Sistema de NEXUS

**Versión:** 2.0
**Estado:** Arquitectura lógica consolidada
**Modelo:** Observabilidad continua, detección temprana y respuesta preventiva

---

# 1. Objetivo

Definir cómo FACT CENTRAL y NEXUS deberán medir, interpretar y supervisar permanentemente la salud operacional del sistema.

El modelo deberá permitir detectar:

* degradación;
* saturación;
* errores;
* fallas;
* pérdida de redundancia;
* anomalías;
* crecimiento peligroso;
* problemas de almacenamiento;
* problemas de red;
* problemas de base de datos;
* fallas de APIs;
* fallas de nodos;
* colas saturadas;
* procesamiento anormal.

El objetivo principal será detectar problemas **antes de que afecten gravemente la operación o la integridad de los datos**.

---

# 2. Principio fundamental

> FACT CENTRAL NO DEBERÁ ESPERAR A FALLAR PARA SABER QUE EXISTE UN PROBLEMA.

NEXUS deberá observar continuamente el comportamiento del sistema y determinar si:

```text
TODO ESTÁ BIEN
↓
ALGO ESTÁ EMPEORANDO
↓
EXISTE RIESGO
↓
EXISTE FALLA
```

---

# 3. Estados globales de salud

FACT CENTRAL utilizará estados operativos generales.

## HEALTHY

Funcionamiento normal.

## OBSERVATION

Existe una desviación leve.

## DEGRADED

Un componente funciona con capacidad reducida.

## HIGH RISK

Existe riesgo significativo de interrupción.

## CRITICAL

Existe falla grave o riesgo inmediato.

## RECOVERY

El sistema está siendo restaurado.

## SAFE MODE

La integridad no puede garantizarse plenamente y se aplican restricciones.

---

# 4. Health Score

NEXUS podrá calcular un indicador global:

```text
100 = Excelente
80–99 = Saludable
60–79 = Observación
40–59 = Degradado
20–39 = Alto riesgo
0–19 = Crítico
```

Este indicador se denominará:

**System Health Score**

No sustituirá las métricas individuales.

---

# 5. Salud por componente

Cada componente tendrá su propio Health Score.

Ejemplo:

```text
API                 95
PostgreSQL          91
Queue               88
Processing          72
Storage             64
Backups             100
Network             93
```

Esto permitirá identificar rápidamente dónde está el problema.

---

# 6. Componentes supervisados

NEXUS deberá supervisar como mínimo:

* Edge / Cloudflare;
* Load Balancer;
* Frontend;
* API Nodes;
* Backend;
* Queue;
* Event Bus;
* Redis;
* PostgreSQL;
* Storage Manager;
* Storage Nodes;
* Processing Nodes;
* OCR;
* IA;
* agentes;
* Scheduler;
* red;
* backups;
* réplicas;
* integraciones externas.

---

# 7. Salud de nodos

Cada nodo deberá reportar:

```text
node_id
estado
CPU
RAM
GPU
temperatura cuando disponible
disco
I/O
red
uptime
workers
latencia
errores
```

---

# 8. Estados de nodo

```text
ONLINE
DEGRADED
DRAINING
OFFLINE
RECOVERING
MAINTENANCE
UNKNOWN
```

---

# 9. CPU

Se supervisará:

* utilización actual;
* promedio;
* picos;
* tiempo sostenido;
* tendencia.

Ejemplo conceptual:

```text
<60 %     NORMAL
60–75 %   OBSERVACIÓN
75–90 %   ALTO
>90 %     CRÍTICO
```

Los valores serán configurables.

---

# 10. RAM

Se medirá:

* RAM utilizada;
* RAM disponible;
* swap;
* memory pressure;
* crecimiento.

No deberá considerarse saludable únicamente porque todavía exista memoria libre.

---

# 11. Almacenamiento

Storage Health deberá considerar:

* utilización;
* espacio libre;
* I/O;
* errores;
* salud del dispositivo;
* redundancia;
* réplica;
* velocidad de crecimiento.

---

# 12. Estados de almacenamiento

Ejemplo:

```text
<60 %       HEALTHY
60–70 %     NORMAL
70–80 %     OBSERVATION
80–90 %     HIGH RISK
>90 %       CRITICAL
```

Los valores serán configurables.

---

# 13. Forecasting de almacenamiento

No se evaluará únicamente el porcentaje actual.

Ejemplo:

```text
Uso actual:
72 %

Crecimiento:
10 % mensual

Proyección:
80 % en 24 días
```

Aunque 72 % no sea crítico, NEXUS podrá generar una advertencia preventiva.

---

# 14. Salud de Storage Pool

El Health Score del Storage Pool deberá considerar:

* capacidad;
* redundancia;
* nodos disponibles;
* discos fallidos;
* réplicas pendientes;
* objetos sin réplica;
* rebalanceo;
* errores.

---

# 15. Salud de PostgreSQL

Se medirán:

```text
conexiones
pool
CPU
RAM
I/O
latencia
queries lentas
locks
deadlocks
errores
replication lag
storage
```

---

# 16. Database Health Score

El estado de PostgreSQL no deberá depender únicamente de que el servicio responda.

Ejemplo:

```text
Servicio online:
Sí

Queries:
8 segundos

Resultado:
DEGRADED
```

Un sistema lento también puede estar enfermo.

---

# 17. Replication Lag

Cuando exista réplica PostgreSQL se medirá:

```text
PRIMARY
↓
REPLICA
```

y el retraso entre ambas.

Un lag excesivo deberá generar alerta.

---

# 18. Salud de Queue

Se observarán:

* jobs pendientes;
* jobs procesados;
* velocidad de entrada;
* velocidad de salida;
* edad del job más antiguo;
* errores;
* reintentos;
* dead-letter jobs.

---

# 19. Queue Growth

Ejemplo:

```text
Entrada:
10,000 jobs/h

Salida:
7,000 jobs/h

Resultado:
+3,000 jobs/h
```

NEXUS deberá detectar que la cola se está deteriorando aunque todavía no esté llena.

---

# 20. Queue Health Score

Podrá considerar:

```text
profundidad
growth rate
job age
workers
failure rate
```

---

# 21. Salud de Processing Nodes

Se supervisará:

* workers activos;
* trabajos/minuto;
* duración promedio;
* errores;
* reintentos;
* CPU;
* RAM;
* cola asignada.

---

# 22. Salud OCR

Se medirán:

```text
documentos pendientes
páginas pendientes
páginas/minuto
errores
reintentos
tiempo promedio
confidence score
```

Un aumento anormal de baja confianza OCR deberá generar señal.

---

# 23. Salud IA

Se medirá:

* disponibilidad;
* latencia;
* errores;
* rate limits;
* costos anormales;
* respuestas inválidas;
* reintentos;
* fallback.

---

# 24. Calidad de procesamiento

System Health deberá observar también calidad, no solo velocidad.

Ejemplo:

```text
OCR rápido
pero
40 % baja confianza
```

Resultado:

```text
PROCESSING QUALITY DEGRADED
```

---

# 25. Salud de API

Se medirá:

```text
requests/segundo
latencia
errores 4xx
errores 5xx
timeouts
conexiones
rate limits
```

---

# 26. Latencia

NEXUS utilizará percentiles cuando corresponda.

Ejemplo:

```text
P50
P95
P99
```

Esto evitará que un promedio oculte solicitudes extremadamente lentas.

---

# 27. Salud del Load Balancer

Se supervisará:

* nodos disponibles;
* distribución;
* errores;
* conexiones;
* health checks.

---

# 28. Salud de Cloudflare / Edge

Se medirán, cuando la integración lo permita:

* errores;
* bloqueos;
* rate limiting;
* tráfico anormal;
* disponibilidad;
* latencia.

---

# 29. Salud de red

Se observará:

```text
latencia
packet loss
ancho de banda
errores
desconexiones
```

---

# 30. Pérdida de conexión local

Un nodo local que pierda conectividad deberá pasar a:

```text
DEGRADED
```

o:

```text
OFFLINE
```

según duración.

No deberá considerarse destruido automáticamente.

---

# 31. Salud de Event Bus

Se supervisará:

* eventos publicados;
* eventos procesados;
* lag;
* consumidores;
* errores;
* reintentos.

---

# 32. Salud de agentes

Cada agente podrá reportar:

```text
runs
success
failures
latency
cost
retries
last_execution
```

---

# 33. Agente degradado

Si un agente falla repetidamente:

```text
AGENT_DEGRADED
```

NEXUS podrá:

* reducir prioridad;
* aislar;
* reiniciar;
* enviar a revisión.

---

# 34. Scheduler Health

Se verificará:

* jobs esperados;
* jobs ejecutados;
* retrasos;
* fallos;
* jobs perdidos.

---

# 35. Backup Health

El sistema deberá conocer:

```text
último backup
resultado
integridad
edad
retención
último restore test
```

---

# 36. Backup no verificado

Si existe backup pero nunca fue validado:

```text
BACKUP EXISTS
BUT
RECOVERY CONFIDENCE LOW
```

Esto reducirá el Recovery Readiness Score.

---

# 37. Replica Health

Se supervisará:

* sincronización;
* errores;
* lag;
* última actualización;
* objetos pendientes.

---

# 38. Redundancy Health

NEXUS deberá responder:

> ¿Cuántas copias válidas existen de la información crítica?

Ejemplo:

```text
Objetivo:
3

Disponibles:
2

Estado:
DEGRADED
```

---

# 39. Integridad documental

Se podrán ejecutar verificaciones periódicas de checksum.

Ejemplo:

```text
document_id
stored_checksum
current_checksum
```

Si no coinciden:

```text
INTEGRITY_ALERT
```

---

# 40. Salud de uploads

Se medirá:

* uploads iniciados;
* completados;
* interrumpidos;
* corruptos;
* reanudados;
* velocidad;
* errores.

---

# 41. Upload Failure Rate

Si el porcentaje de cargas fallidas aumenta:

```text
UPLOAD_HEALTH_DEGRADED
```

Esto podría indicar:

* red;
* Cloudflare;
* storage;
* backend;
* cliente.

---

# 42. Anomaly Detection

NEXUS deberá identificar comportamientos anormales.

Ejemplo:

```text
Promedio:
1,000 uploads/h

Actual:
20,000 uploads/h
```

No deberá asumir automáticamente que es ataque.

Primero clasificará el evento.

---

# 43. Diferenciación de pico legítimo

Se utilizarán señales como:

* autenticación;
* tenants;
* patrones históricos;
* origen;
* documentación cargada;
* volumen;
* comportamiento.

---

# 44. Anomalía de tráfico

Un pico podrá clasificarse:

```text
LEGITIMATE_SPIKE
SUSPICIOUS
ATTACK
UNKNOWN
```

---

# 45. Alertas

Las alertas deberán tener severidad.

```text
INFO
WARNING
HIGH
CRITICAL
```

---

# 46. Alert Fatigue

NEXUS deberá evitar generar cientos de alertas por el mismo incidente.

Las alertas relacionadas podrán agruparse.

Ejemplo:

```text
Storage Full
↓
Queue Slow
↓
Processing Slow
```

podrán formar parte de un mismo incidente raíz.

---

# 47. Correlación de eventos

NEXUS deberá intentar determinar causa raíz.

Ejemplo:

```text
SSD-01 lento
↓
Storage latency
↓
Queue backlog
↓
Processing slowdown
```

La alerta principal será:

```text
ROOT CAUSE:
SSD-01 degradation
```

---

# 48. Health Timeline

Cada incidente tendrá timeline.

```text
10:20 WARNING
10:25 DEGRADED
10:31 HIGH RISK
10:34 FAILOVER
10:38 HEALTHY
```

---

# 49. Health History

Se conservará historial para analizar:

* tendencias;
* fallas repetidas;
* degradación;
* capacidad;
* mantenimiento.

---

# 50. Predictive Health

NEXUS deberá intentar predecir problemas.

Ejemplo:

```text
Disco:
73 %

Crecimiento:
8 % mensual

Predicción:
HIGH RISK en 6 semanas
```

---

# 51. Predictive Failure

Cuando existan datos suficientes podrán analizarse señales como:

* errores de disco;
* temperatura;
* latencia;
* reinicios;
* fallos recurrentes.

---

# 52. System Health Dashboard

Ruta propuesta:

**Administración → Infraestructura → Salud del Sistema**

Deberá mostrar:

```text
System Health Score
Capacity Score
Recovery Readiness
Cost Efficiency
Nodes
Database
Storage
Queue
API
Processing
Backups
Alerts
```

---

# 53. Vista ejecutiva

Ejemplo:

```text
SYSTEM HEALTH
92 / 100
HEALTHY

Capacidad:
73 %

Storage:
68 %

Database:
94 %

Processing:
81 %

Recovery:
98 %
```

---

# 54. Vista técnica

Permitirá profundizar en:

* nodo;
* servicio;
* métricas;
* eventos;
* logs;
* dependencias.

---

# 55. Health Check activo

Los servicios deberán responder a health checks.

Ejemplo:

```text
/health
/ready
/live
```

La implementación concreta dependerá de la tecnología.

---

# 56. Liveness

Responde:

> ¿El proceso está vivo?

---

# 57. Readiness

Responde:

> ¿Está preparado para recibir trabajo?

Un nodo puede estar vivo pero no listo.

---

# 58. Ejemplo

```text
NODE ONLINE
CPU 100 %
Queue local bloqueada

Liveness:
YES

Readiness:
NO
```

El Load Balancer deberá dejar de enviarle nuevas cargas.

---

# 59. Maintenance Mode

Un nodo podrá pasar a:

```text
MAINTENANCE
```

El sistema dejará de asignarle nuevos trabajos y permitirá terminar los actuales.

---

# 60. Drain Mode

Antes de retirar un nodo:

```text
ACTIVE
↓
DRAINING
↓
0 JOBS
↓
OFFLINE
```

---

# 61. Auto-Healing

NEXUS podrá ejecutar acciones previamente autorizadas.

Ejemplos:

```text
restart worker
restart service
remove node from load balancer
reassign jobs
activate replica
```

---

# 62. Auto-Scaling

System Health enviará señales a Capacity Planning.

Ejemplo:

```text
Queue growth
+
CPU sustained high
↓
Capacity Manager
↓
Scale recommendation
```

---

# 63. Safe Automation

No todas las acciones serán automáticas.

Se distinguirán:

```text
AUTO
APPROVAL_REQUIRED
MANUAL_ONLY
```

---

# 64. Ejemplo de acción automática

```text
Worker crashed
↓
restart worker
```

---

# 65. Ejemplo de aprobación

```text
Storage projected critical
↓
add new infrastructure
↓
ADMIN APPROVAL
```

---

# 66. Emergency Action

Determinadas acciones podrán ejecutarse automáticamente para proteger datos.

Ejemplo:

```text
storage corruption detected
↓
STOP WRITES
↓
SAFE MODE
```

---

# 67. Integración con Capacity Planning

`26C_CAPACITY_PLANNING.md` utiliza las métricas de este documento para decidir:

> ¿NECESITAMOS MÁS CAPACIDAD?

---

# 68. Integración con Infrastructure Topology

`26A_INFRASTRUCTURE_TOPOLOGY.md` indica qué componentes existen.

System Health observa cada uno.

---

# 69. Integración con Disaster Recovery

`26B_DISASTER_RECOVERY_PLAN.md` utiliza las alertas de System Health para iniciar recuperación.

```text
DETECT
↓
CLASSIFY
↓
RECOVER
```

---

# 70. Integración con Cost Model

`26D_INFRASTRUCTURE_COST_MODEL.md` utiliza métricas de utilización para evaluar eficiencia económica.

---

# 71. Integración con Resource Engine

`15_RESOURCE_ENGINE.md` utilizará Health Data para distribuir recursos.

---

# 72. Integración con Executive Intelligence

`16_EXECUTIVE_INTELLIGENCE_ENGINE.md` convertirá problemas técnicos en recomendaciones entendibles.

Ejemplo:

```text
Storage Pool 81 %
```

se podrá traducir a:

> Se recomienda ampliar almacenamiento dentro de aproximadamente 30 días.

---

# 73. Integración con Autonomous Operations Center

`26F_AUTONOMOUS_OPERATIONS_CENTER.md` utilizará System Health como una de sus principales fuentes de información.

---

# 74. Health Event

Cada cambio importante deberá generar un evento.

Ejemplo:

```text
system.health.degraded
node.offline
storage.capacity.warning
database.replication.lag
queue.backlog.high
backup.failed
```

La nomenclatura definitiva deberá respetar el catálogo oficial de eventos.

---

# 75. Telemetría

NEXUS utilizará tres pilares:

```text
METRICS
LOGS
TRACES
```

---

# 76. Metrics

Permitirán medir:

```text
CPU
RAM
latencia
requests
jobs
storage
```

---

# 77. Logs

Permitirán conocer qué ocurrió.

---

# 78. Traces

Permitirán seguir una operación entre múltiples servicios.

Ejemplo:

```text
UPLOAD
↓
API
↓
STORAGE
↓
QUEUE
↓
OCR
↓
DATABASE
```

---

# 79. Correlation ID

Toda operación distribuida deberá poder utilizar un identificador de correlación.

Ejemplo:

```text
correlation_id:
FC-TRACE-938472
```

Esto permitirá seguir el recorrido completo.

---

# 80. Observabilidad centralizada

Aunque existan:

```text
VPS
PC-01
PC-02
PC-03
```

Administración deberá observarlos desde un único panel lógico.

---

# 81. Pérdida de telemetría

Si un nodo deja de reportar:

```text
UNKNOWN
```

No deberá asumirse inmediatamente que está muerto.

Se ejecutarán comprobaciones adicionales.

---

# 82. Heartbeat

Los nodos podrán enviar:

```text
HEARTBEAT
```

periódicamente.

Si desaparece durante un periodo configurado:

```text
NODE_UNREACHABLE
```

---

# 83. Health Policies

Los límites deberán ser configurables.

No deberán quedar rígidamente escritos en código.

Ejemplo:

```text
cpu_warning
cpu_critical
storage_warning
storage_critical
queue_warning
```

---

# 84. Políticas por nodo

Una PC pequeña no deberá tener necesariamente los mismos límites que una VPS grande.

---

# 85. Políticas por servicio

Un servicio OCR podrá tolerar una cola mayor que autenticación.

---

# 86. Baseline

NEXUS deberá aprender cuál es el comportamiento normal.

Ejemplo:

```text
Lunes 09:00
normal:
4,000 requests/min
```

Entonces 4,000 no deberá considerarse automáticamente anomalía.

---

# 87. Dynamic Thresholds

Cuando exista suficiente información, algunos límites podrán adaptarse al comportamiento histórico.

---

# 88. No ocultar métricas reales

Aunque existan Health Scores, Administración deberá poder revisar los valores originales.

---

# 89. Auditoría

Toda acción automática generada por System Health deberá registrar:

```text
qué detectó
qué decidió
qué ejecutó
por qué
resultado
```

---

# 90. Health Data Retention

Las métricas históricas podrán tener políticas de retención.

Ejemplo:

```text
alta resolución:
30 días

agregada:
1 año

histórica:
mayor periodo
```

Los valores exactos serán configurables.

---

# 91. Health SLA

Cada componente podrá tener objetivos internos.

Ejemplo conceptual:

```text
API availability
Storage availability
Database availability
```

Los SLA reales se definirán cuando exista infraestructura productiva.

---

# 92. Health Dependencies

El Health Score global deberá reconocer dependencias.

Ejemplo:

```text
OCR = OFFLINE
```

no necesariamente significa:

```text
FACT CENTRAL = OFFLINE
```

El ERP podrá continuar recibiendo documentos.

Resultado:

```text
SYSTEM DEGRADED
```

no:

```text
SYSTEM DOWN
```

---

# 93. Critical Path

NEXUS deberá identificar servicios críticos:

```text
AUTH
UPLOAD
DURABLE STORAGE
DATABASE
QUEUE
```

Si alguno falla, el impacto será mayor.

---

# 94. Non-Critical Path

Ejemplo:

```text
REPORTING
ANALYTICS
LEARNING
```

podrán detenerse sin detener el ERP completo.

---

# 95. Estado parcial

FACT CENTRAL podrá mostrar:

```text
ERP:
ONLINE

Uploads:
ONLINE

OCR:
DEGRADED

Reports:
OFFLINE
```

Esto es mejor que mostrar simplemente:

```text
SYSTEM ERROR
```

---

# 96. Regla de integridad

> UN SISTEMA RÁPIDO PERO CORRUPTO NO ESTÁ SALUDABLE.

System Health deberá incluir integridad como dimensión principal.

---

# 97. Regla de disponibilidad

> UN COMPONENTE OFFLINE NO DEBERÁ CONVERTIR AUTOMÁTICAMENTE A TODO FACT CENTRAL EN OFFLINE SI EXISTE UNA RUTA ALTERNATIVA.

---

# 98. Regla de predicción

> NEXUS DEBERÁ INTENTAR RESOLVER LOS PROBLEMAS ANTES DE QUE SE CONVIERTAN EN INCIDENTES.

---

# 99. Flujo general

```text
INFRASTRUCTURE
      │
      ▼
TELEMETRY
      │
      ▼
SYSTEM HEALTH
      │
 ┌────┼────────┐
 ▼    ▼        ▼
OK  WARNING  CRITICAL
              │
              ▼
         ROOT CAUSE
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
 AUTO-HEAL  SCALE   RECOVERY
     │        │        │
     └────────┼────────┘
              ▼
           VERIFY
              │
              ▼
           HEALTHY
```

---

# 100. Estado del documento

**SYSTEM HEALTH MODEL — ARQUITECTURA LÓGICA DEFINIDA**

Los umbrales exactos deberán calibrarse durante pruebas y producción.

La arquitectura queda diseñada para observar FACT CENTRAL como un sistema distribuido, detectar degradaciones tempranas, correlacionar fallas y alimentar los mecanismos de escalamiento, recuperación y operación autónoma.
