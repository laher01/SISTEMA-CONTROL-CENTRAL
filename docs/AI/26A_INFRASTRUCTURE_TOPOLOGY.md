# 26A — INFRASTRUCTURE TOPOLOGY

# FACT CENTRAL

## Topología Oficial de Infraestructura de NEXUS

**Versión:** 2.0
**Estado:** Arquitectura lógica consolidada
**Modelo:** Distribuido, escalable y tolerante a fallos

---

# 1. Objetivo

Definir la topología física y lógica oficial de la infraestructura que soportará FACT CENTRAL y NEXUS.

Este documento establece cómo deberán distribuirse:

* acceso público;
* Cloudflare;
* frontend;
* API;
* adquisición documental;
* colas;
* procesamiento;
* motores NEXUS;
* agentes;
* PostgreSQL;
* almacenamiento;
* réplicas;
* backups;
* nodos locales;
* VPS;
* observabilidad;
* seguridad.

La infraestructura deberá poder crecer sin modificar las reglas fundamentales del ERP.

---

# 2. Principio fundamental

> FACT CENTRAL NO DEBERÁ DEPENDER DE UNA MÁQUINA ESPECÍFICA.

La aplicación deberá funcionar sobre una infraestructura compuesta por nodos reemplazables.

Un servidor, VPS, PC, SSD o worker podrá incorporarse, retirarse o reemplazarse sin alterar la identidad de los documentos ni las reglas de negocio.

---

# 3. Filosofía de infraestructura

NEXUS deberá poder operar en diferentes escalas:

```text
DESARROLLO LOCAL
↓
NODO LOCAL
↓
VPS
↓
MÚLTIPLES NODOS
↓
CLUSTER DISTRIBUIDO
```

La arquitectura lógica será la misma.

Lo que cambia será la cantidad y capacidad de recursos disponibles.

---

# 4. Principios obligatorios

Toda infraestructura FACT CENTRAL deberá ser:

* modular;
* desacoplada;
* observable;
* escalable;
* redundante;
* recuperable;
* automatizable;
* segura;
* distribuible;
* tolerante a fallos.

---

# 5. Arquitectura general

```text
                         USUARIOS / GESTORES
                                │
                                ▼
                             INTERNET
                                │
                                ▼
                        CLOUDFLARE / EDGE
                                │
                                ▼
                         LOAD BALANCER
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
             FRONTEND                       API LAYER
                                               │
                                               ▼
                                         API GATEWAY
                                               │
                      ┌────────────────────────┼────────────────────────┐
                      ▼                        ▼                        ▼
                UPLOAD SERVICE          APPLICATION CORE          AUTH / SECURITY
                      │                        │
                      ▼                        ▼
                DURABLE STORAGE            NEXUS CORE
                      │                        │
               INTEGRITY CHECK               │
                      │                        ▼
                      ▼                    EVENT BUS
                    QUEUE                      │
                      │                        ▼
          ┌───────────┼───────────┐       ORCHESTRATION
          ▼           ▼           ▼            │
       NODE A      NODE B      NODE C          ▼
       WORKERS     WORKERS     WORKERS       AGENTS
          │           │           │
          └───────────┼───────────┘
                      ▼
                 PROCESSING
                OCR / IA / DATA
                      │
                      ▼
                   VALIDATION
                      │
                      ▼
                  POSTGRESQL
                      │
                      ▼
                STORAGE MANAGER
             ┌────────┼─────────┐
             ▼        ▼         ▼
          STORAGE A STORAGE B STORAGE C
             │
             └────────┬─────────┘
                      ▼
                   REPLICA
                      │
                      ▼
                 REMOTE BACKUP
```

---

# 6. Capas de infraestructura

FACT CENTRAL deberá dividirse en capas independientes.

## Capa 1 — Edge

Responsable de:

* DNS;
* HTTPS;
* protección;
* filtrado;
* WAF;
* rate limiting;
* mitigación de ataques;
* entrada de tráfico.

Tecnología posible:

**Cloudflare**

---

# 7. Capa 2 — Frontend

El frontend deberá permanecer desacoplado del backend.

Podrá ejecutarse mediante:

* Cloudflare Pages;
* CDN;
* hosting estático;
* infraestructura equivalente.

El frontend nunca deberá acceder directamente a PostgreSQL.

---

# 8. Capa 3 — API

Las solicitudes deberán pasar por una capa API escalable.

```text
LOAD BALANCER
      │
 ┌────┼────┐
 ▼    ▼    ▼
API1 API2 API3
```

Los nodos API deberán ser:

* reemplazables;
* stateless siempre que sea posible;
* escalables horizontalmente.

Agregar nuevos API Nodes no deberá requerir modificar el código de negocio.

---

# 9. API Gateway

El API Gateway centralizará:

* autenticación;
* autorización;
* validación;
* rutas;
* políticas;
* límites;
* identificación de tenant;
* trazabilidad;
* seguridad.

---

# 10. Capa de adquisición documental

Las cargas de documentos deberán utilizar un canal especializado.

```text
GESTOR
  ↓
UPLOAD SERVICE
  ↓
DURABLE STORAGE
  ↓
CHECKSUM
  ↓
VERIFIED
  ↓
QUEUE
```

La adquisición deberá estar desacoplada del procesamiento.

---

# 11. Regla de adquisición

> NINGÚN DOCUMENTO PODRÁ SER PROCESADO ANTES DE CONFIRMAR SU RECEPCIÓN COMPLETA E INTEGRIDAD.

Si una conexión se interrumpe:

```text
UPLOAD_INTERRUPTED
```

El archivo no llegará a OCR, IA ni procesamiento normal.

---

# 12. Durable Storage

Los archivos originales deberán almacenarse antes de su procesamiento.

El almacenamiento deberá soportar:

* persistencia;
* integridad;
* identificación única;
* control de versiones cuando corresponda;
* redundancia;
* recuperación.

El archivo original deberá considerarse evidencia primaria.

---

# 13. Sistema de colas

La cola será el punto de desacoplamiento entre adquisición y procesamiento.

Ejemplo:

```text
20,000 DOCUMENTOS
       ↓
      QUEUE
       ↓
 WORKERS DISPONIBLES
```

La cola permitirá que FACT CENTRAL reciba más trabajo del que puede procesar instantáneamente sin colapsar.

---

# 14. Topología de procesamiento

Se utilizarán múltiples nodos.

```text
                  JOB QUEUE
              ┌──────┼──────┐
              ▼      ▼      ▼
           NODE 1  NODE 2  NODE 3
              │      │      │
          WORKERS WORKERS WORKERS
```

Cada nodo podrá ejecutar diferentes tipos de workers.

---

# 15. Workers

Tipos posibles:

```text
OCR Worker
PDF Worker
Image Worker
Classification Worker
Extraction Worker
Duplicate Worker
Association Worker
AI Worker
Report Worker
Notification Worker
Integration Worker
Agent Worker
```

Los workers deberán consumir trabajos desde colas y no depender directamente unos de otros.

---

# 16. Nodo FACT CENTRAL

Cualquier servidor autorizado podrá convertirse en un nodo.

Podrá ser:

* VPS;
* servidor físico;
* PC;
* workstation;
* servidor GPU;
* nodo de almacenamiento.

Proceso:

```text
NEW NODE
↓
REGISTER
↓
IDENTITY CHECK
↓
SECURITY CHECK
↓
ADMIN APPROVAL
↓
RESOURCE PROFILE
↓
ROLE ASSIGNMENT
↓
ACTIVE
```

---

# 17. Node Manager

NEXUS deberá disponer de un Node Manager.

El Administrador podrá consultar:

```text
Nodo
Estado
CPU
RAM
GPU
Storage
Red
Latencia
Rol
Carga
Salud
```

Ejemplo:

| Nodo       | Estado | Función          |
| ---------- | ------ | ---------------- |
| VPS-01     | ONLINE | API + Processing |
| VPS-02     | ONLINE | Processing       |
| PC-01      | ONLINE | OCR + Processing |
| PC-02      | ONLINE | Processing       |
| STORAGE-01 | ONLINE | Storage          |
| STORAGE-02 | ONLINE | Replica          |

---

# 18. Incorporación de nuevas PCs

Cuando FACT CENTRAL sea instalado en una nueva PC, esa máquina podrá funcionar únicamente como cliente o convertirse en nodo.

El Administrador podrá decidir:

```text
CLIENT ONLY
PROCESSING NODE
OCR NODE
AI NODE
STORAGE NODE
REPLICA NODE
BACKUP NODE
```

Una nueva instalación no deberá convertirse automáticamente en un nodo crítico sin autorización.

---

# 19. Recursos heterogéneos

Los nodos no necesitan tener las mismas características.

Ejemplo:

```text
PC A
Core i5
16 GB RAM
SSD 500 GB

ROL:
Workers ligeros
Validación
Clasificación
```

```text
PC B
Ryzen 9
64 GB RAM
GPU
SSD 4 TB

ROL:
IA
OCR
Procesamiento pesado
```

NEXUS podrá recomendar automáticamente el mejor rol.

---

# 20. Nodos de procesamiento mínimos

Para producción con alta disponibilidad se recomienda conceptualmente:

```text
PROCESSING NODE A
+
PROCESSING NODE B
```

Ambos deberán poder consumir trabajos pendientes.

La caída de un nodo no deberá detener todo el sistema.

---

# 21. VPS y nodos locales

FACT CENTRAL podrá operar con una combinación híbrida.

Ejemplo:

```text
VPS-01
API + Orchestration

VPS-02
Processing

PC-NEXOMAR-01
Processing

PC-NEXOMAR-02
OCR

PC-NEXOMAR-03
Replica / Processing
```

Los nodos locales deberán conectarse mediante canales seguros.

---

# 22. Segmento público

Podrá contener:

* Cloudflare;
* DNS;
* frontend;
* endpoints públicos controlados.

Nunca deberá contener directamente:

* PostgreSQL;
* Redis;
* almacenamiento interno;
* backups.

---

# 23. Segmento aplicación

Contendrá:

* API;
* NEXUS;
* motores;
* agentes;
* scheduler;
* orchestration;
* workers;
* integración.

---

# 24. Segmento de datos

Contendrá:

* PostgreSQL;
* Redis o equivalente;
* colas;
* storage;
* réplicas.

No deberá ser directamente accesible desde Internet.

---

# 25. Segmento de administración

Contendrá:

* panel administrativo;
* observabilidad;
* monitoreo;
* gestión de nodos;
* gestión de capacidad;
* alertas;
* auditoría.

Acceso restringido.

---

# 26. PostgreSQL

PostgreSQL será la principal fuente lógica de verdad estructurada.

Deberá manejar:

* usuarios;
* gestores;
* empresas;
* documentos;
* expedientes;
* estados;
* relaciones;
* auditoría;
* metadatos;
* storage keys.

Los documentos binarios no deberán almacenarse indiscriminadamente dentro de PostgreSQL.

---

# 27. Pool de conexiones

Los clientes y gestores nunca deberán abrir conexiones directas contra PostgreSQL.

Flujo:

```text
USUARIO
  ↓
API
  ↓
POOL
  ↓
POSTGRESQL
```

El pool deberá controlar el crecimiento de conexiones.

---

# 28. Replicación de PostgreSQL

Cuando la escala lo requiera:

```text
POSTGRESQL PRIMARY
        │
        ▼
POSTGRESQL REPLICA
```

Las réplicas podrán utilizarse para:

* disponibilidad;
* consultas;
* recuperación;
* reducción de carga.

---

# 29. Storage Manager

FACT CENTRAL utilizará una capa denominada:

**Storage Manager**

La aplicación no deberá conocer directamente discos físicos.

---

# 30. Storage Pool

Ejemplo:

```text
SSD A 1 TB
SSD B 2 TB
NAS   4 TB
Cloud Storage 10 TB
       ↓
STORAGE MANAGER
       ↓
STORAGE POOL
```

FACT CENTRAL verá una capacidad lógica.

---

# 31. Selección de almacenamiento

Storage Manager decidirá dónde guardar información según:

* capacidad disponible;
* salud;
* latencia;
* rendimiento;
* redundancia;
* ubicación;
* tipo de archivo.

No se requerirá seleccionar manualmente:

```text
D:
E:
F:
```

para cada documento.

---

# 32. Identidad documental

Un documento deberá identificarse mediante:

```text
document_id
storage_key
checksum
```

Nunca mediante su ubicación física.

Ejemplo correcto:

```text
DOC-938472
storage_key:
factcentral/2026/07/DOC-938472
```

---

# 33. Rebalanceo de almacenamiento

Cuando un disco alcance niveles elevados:

```text
STORAGE A = 85 %
STORAGE B = 35 %
```

Storage Manager podrá:

* priorizar B;
* detener nuevas escrituras en A;
* mover objetos;
* rebalancear;
* generar alertas.

---

# 34. Expansión

Nuevo almacenamiento:

```text
NEW SSD / NAS / STORAGE
↓
DETECTION
↓
HEALTH CHECK
↓
ADMIN APPROVAL
↓
STORAGE POOL
↓
AVAILABLE
```

No deberá ser necesario modificar el ERP.

---

# 35. Réplica documental

FACT CENTRAL deberá permitir múltiples copias de disponibilidad.

Ejemplo:

```text
PRIMARY STORAGE
       │
       ├──────────────┐
       ▼              ▼
LOCAL REPLICA     REMOTE REPLICA
```

La réplica permitirá continuidad operativa.

---

# 36. Backup

El backup se mantendrá independiente de las réplicas.

```text
PRIMARY
↓
REPLICA
↓
BACKUP HISTÓRICO
```

Una réplica no sustituye al backup.

---

# 37. Copias geográficamente separadas

Al menos una copia crítica deberá poder ubicarse fuera de la ubicación física principal.

Ejemplo:

```text
PAITA
Primary

PIURA / VPS / CLOUD
Remote Replica

BACKUP EXTERNO
Historical Backup
```

Esto reduce riesgo por:

* robo;
* incendio;
* inundación;
* daño eléctrico;
* pérdida física completa del local.

---

# 38. SSD externos

SSD USB podrá utilizarse principalmente para:

* backup;
* recuperación;
* archivo;
* copia adicional.

No deberá ser la única fuente primaria de datos operativos.

---

# 39. Redis / Cache

Redis o tecnología equivalente podrá utilizarse para:

* cache;
* sesiones;
* locks;
* tareas temporales;
* coordinación;
* colas cuando corresponda.

No deberá convertirse en fuente única de información crítica.

---

# 40. Event Bus

NEXUS utilizará un sistema de eventos.

```text
ENGINE
↓
EVENT BUS
↓
ROUTER
↓
CONSUMERS
```

Los consumidores deberán funcionar desacoplados.

---

# 41. Integraciones externas

Entre ellas podrán existir:

* SUNAT;
* APIPERU;
* OpenAI;
* servicios OCR;
* correo;
* WhatsApp;
* Google Drive;
* Cloudflare;
* almacenamiento remoto.

Todas deberán accederse mediante canales seguros.

---

# 42. Rate Limiting externo

Las integraciones externas utilizarán:

```text
QUEUE
↓
RATE LIMITER
↓
WORKER
↓
EXTERNAL API
```

Esto evitará saturar proveedores externos.

---

# 43. Cloudflare

Cloudflare será una capa de protección y entrada, no la única capa de continuidad.

La infraestructura deberá distinguir tráfico legítimo de:

* abuso;
* bots;
* ataques;
* picos anormales.

Los límites deberán configurarse teniendo en cuenta que FACT CENTRAL puede generar altos volúmenes legítimos.

La configuración exacta deberá revisarse contra las capacidades vigentes del proveedor durante implementación.

---

# 44. Load Balancer

El Load Balancer distribuirá:

* sesiones;
* API;
* solicitudes;
* backend;
* workers cuando corresponda.

Ejemplo:

```text
              LOAD BALANCER
        ┌─────────┼─────────┐
        ▼         ▼         ▼
      API-1     API-2     API-3
```

---

# 45. Escalamiento horizontal

Cuando aumente la carga:

```text
API-1
API-2
```

podrá convertirse en:

```text
API-1
API-2
API-3
API-4
API-5
```

sin modificar reglas del ERP.

---

# 46. Escalamiento vertical

También podrá aumentarse:

* CPU;
* RAM;
* almacenamiento;
* ancho de banda;
* I/O.

Será utilizado cuando resulte más conveniente que agregar nodos.

---

# 47. Alta disponibilidad

FACT CENTRAL deberá evitar puntos únicos de falla en los servicios críticos.

Se buscará progresivamente:

* múltiples API Nodes;
* múltiples Processing Nodes;
* PostgreSQL Replica;
* almacenamiento redundante;
* colas persistentes;
* failover;
* backup externo.

---

# 48. Falla de un nodo

Si:

```text
NODE A
OFFLINE
```

la cola deberá continuar disponible.

Otros nodos podrán tomar trabajos pendientes.

```text
QUEUE
 │
 ├── NODE B
 └── NODE C
```

---

# 49. Falla total de procesamiento

Si todos los Processing Nodes están temporalmente offline:

```text
UPLOAD SERVICE = ONLINE
STORAGE = ONLINE
QUEUE = ONLINE
PROCESSING = OFFLINE
```

los documentos podrán permanecer:

```text
VERIFIED
QUEUED
```

hasta recuperar capacidad.

No deberán perderse.

---

# 50. Observabilidad

Todos los nodos deberán reportar:

* estado;
* CPU;
* RAM;
* disco;
* almacenamiento;
* red;
* conexiones;
* latencia;
* errores;
* tareas;
* colas;
* tiempo de procesamiento.

---

# 51. Herramientas de observabilidad

Podrán utilizarse tecnologías como:

* Prometheus;
* Grafana;
* Sentry;
* OpenTelemetry;
* logging centralizado.

La tecnología definitiva podrá variar sin cambiar el modelo lógico.

---

# 52. Seguridad

La infraestructura deberá utilizar:

* HTTPS;
* TLS;
* firewall;
* VPN cuando corresponda;
* JWT o equivalente;
* segmentación;
* tokens temporales;
* cifrado;
* control de accesos;
* auditoría;
* backups cifrados.

---

# 53. Desarrollo local

En desarrollo:

```text
PC / LAPTOP
     ↓
Docker
     ↓
Frontend
Backend
Queue
PostgreSQL
Storage local
```

Este escenario será utilizado para desarrollo y pruebas.

No representa la arquitectura final de producción.

---

# 54. Producción inicial

Ejemplo:

```text
Cloudflare
    ↓
VPS-01
API / NEXUS
    ↓
Queue
    ↓
VPS-02
Workers
    ↓
PostgreSQL
    ↓
Storage
    ↓
Backup
```

---

# 55. Producción híbrida

Ejemplo recomendado para FACT CENTRAL:

```text
                   CLOUDFLARE
                       │
                       ▼
                    VPS-01
                  API / CORE
                       │
                       ▼
                     QUEUE
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
       VPS-02        PC-01         PC-02
      Processing      OCR         Processing
          │            │             │
          └────────────┼─────────────┘
                       ▼
                   POSTGRESQL
                       │
                       ▼
                STORAGE MANAGER
              ┌────────┼────────┐
              ▼        ▼        ▼
          STORAGE-1 STORAGE-2 REMOTE
```

---

# 56. Cluster empresarial

A mayor escala:

```text
CLOUDFLARE
↓
LOAD BALANCER
↓
API CLUSTER
↓
NEXUS CLUSTER
↓
EVENT BUS
↓
QUEUE CLUSTER
↓
PROCESSING CLUSTER
↓
POSTGRESQL CLUSTER
↓
STORAGE CLUSTER
↓
REPLICA
↓
REMOTE BACKUP
```

---

# 57. Escalabilidad

La infraestructura deberá permitir evolucionar:

```text
1 NODE
↓
2 NODES
↓
5 NODES
↓
10 NODES
↓
N NODES
```

sin modificar las reglas de negocio.

---

# 58. Separación lógica

La arquitectura deberá mantener separadas:

```text
EDGE
APPLICATION
PROCESSING
DATA
STORAGE
ADMINISTRATION
BACKUP
```

Esta separación facilitará seguridad, rendimiento y crecimiento.

---

# 59. Integración con Capacity Planning

Este documento trabaja conjuntamente con:

`26C_CAPACITY_PLANNING.md`

Capacity Planning determina:

> cuánta capacidad necesitamos.

Infrastructure Topology determina:

> dónde y cómo se distribuye esa capacidad.

---

# 60. Integración con Disaster Recovery

`26B_DISASTER_RECOVERY_PLAN.md` deberá establecer cómo recuperar esta infraestructura cuando falle:

* nodo;
* disco;
* VPS;
* PostgreSQL;
* Storage;
* conexión;
* ubicación física.

---

# 61. Integración con System Health

`26E_SYSTEM_HEALTH_MODEL.md` vigilará todos los componentes descritos en esta topología.

---

# 62. Integración con Autonomous Operations

`26F_AUTONOMOUS_OPERATIONS_CENTER.md` podrá utilizar la topología para:

* activar nodos;
* redistribuir cargas;
* detectar fallos;
* ejecutar failover;
* generar recomendaciones;
* coordinar recuperación.

---

# 63. Reglas supremas

## Regla 1

> Ninguna máquina específica deberá ser indispensable para la existencia lógica de FACT CENTRAL.

## Regla 2

> Ningún documento deberá depender permanentemente del disco físico donde fue almacenado originalmente.

## Regla 3

> La recepción segura de información tendrá prioridad sobre su procesamiento inmediato.

## Regla 4

> La caída de un Processing Node no deberá implicar pérdida documental.

## Regla 5

> Una nueva máquina autorizada podrá convertirse en un nuevo recurso del ecosistema.

## Regla 6

> La infraestructura crecerá agregando capacidad, no reescribiendo el ERP.

---

# 64. Estado del documento

**INFRASTRUCTURE TOPOLOGY — ARQUITECTURA LÓGICA DEFINIDA**

La infraestructura física exacta podrá evolucionar conforme FACT CENTRAL crezca.

Los proveedores, tecnologías, tamaños de servidores y cantidades de nodos podrán cambiar.

La arquitectura lógica deberá mantenerse estable.
