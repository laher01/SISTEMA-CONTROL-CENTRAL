# 26C — CAPACITY PLANNING

**Proyecto:** FACT CENTRAL
**Plataforma inteligente:** NEXUS
**Documento:** Planificación de Capacidad
**Estado:** Arquitectura definida
**Escala inicial:** 2,000 usuarios principales
**Gestores estimados:** Hasta 40 por usuario
**Universo potencial inicial:** Hasta 80,000 gestores asociados
**Modelo:** Escalamiento dinámico, distribuido y supervisado

---

# 1. Propósito

Este documento define cómo FACT CENTRAL y NEXUS deberán administrar el crecimiento de usuarios, gestores, documentos, solicitudes, procesamiento, almacenamiento y recursos tecnológicos sin requerir el rediseño permanente del ERP.

La arquitectura deberá permitir aumentar capacidad mediante configuración, incorporación de recursos y escalamiento horizontal o vertical, manteniendo estable la lógica de negocio.

La escala deberá considerarse una propiedad operativa configurable y no una limitación rígida escrita dentro del código.

---

# 2. Principio fundamental

FACT CENTRAL deberá ser:

**ELÁSTICO · DISTRIBUIDO · MEDIBLE · REDUNDANTE · ESCALABLE · RECUPERABLE**

El crecimiento de carga no deberá obligar a modificar los algoritmos fundamentales del ERP.

La regla será:

> MÁS DEMANDA DEBERÁ GENERAR MÁS CAPACIDAD, NO LA NECESIDAD DE RECONSTRUIR EL SISTEMA.

---

# 3. Capacidad organizacional inicial

La primera capacidad objetivo será:

| Concepto             |      Capacidad inicial |
| -------------------- | ---------------------: |
| Usuarios principales |                  2,000 |
| Gestores por usuario |     Hasta 40 estimados |
| Gestores potenciales |                 80,000 |
| Procesamiento        |            Distribuido |
| Escalamiento         |  Automático y dinámico |
| Control              | NEXUS + Administración |

Los 40 gestores representan una hipótesis inicial de planificación de capacidad y no deberán convertirse en una limitación rígida del modelo de datos.

Un usuario podrá tener una cantidad diferente de gestores cuando sus permisos, plan o reglas comerciales lo permitan.

---

# 4. Usuarios registrados no equivalen a conexiones simultáneas

FACT CENTRAL distinguirá entre:

* usuarios registrados;
* gestores registrados;
* usuarios activos;
* usuarios concurrentes;
* sesiones;
* solicitudes por segundo;
* cargas documentales;
* procesos intensivos.

Tener 80,000 gestores potenciales no significa mantener 80,000 conexiones permanentes contra PostgreSQL.

La arquitectura deberá desacoplar usuarios, API, procesamiento y base de datos.

---

# 5. Capacity Tiers

FACT CENTRAL utilizará niveles de capacidad.

Ejemplo inicial:

| Tier   | Usuarios principales | Gestores potenciales |
| ------ | -------------------: | -------------------: |
| TIER 1 |                2,000 |               80,000 |
| TIER 2 |                5,000 |              200,000 |
| TIER 3 |               10,000 |              400,000 |
| TIER 4 |               25,000 |            1,000,000 |

Estos valores serán configurables.

Cada Tier podrá definir:

* nodos API;
* workers;
* CPU;
* RAM;
* almacenamiento;
* capacidad de red;
* pool de conexiones;
* capacidad de colas;
* procesamiento OCR;
* procesamiento IA;
* límites operativos.

Los Tiers representan objetivos de planificación y no límites absolutos del software.

---

# 6. Capacity Manager

NEXUS deberá disponer de un componente lógico denominado **Capacity Manager**.

Será responsable de observar:

* crecimiento de usuarios;
* crecimiento de gestores;
* concurrencia;
* solicitudes API;
* CPU;
* RAM;
* almacenamiento;
* ancho de banda;
* profundidad de colas;
* latencia;
* conexiones;
* OCR;
* IA;
* eventos;
* workers;
* crecimiento histórico.

Capacity Manager deberá trabajar conjuntamente con Resource Engine, System Health, Executive Intelligence y Autonomous Operations Center.

---

# 7. Panel administrativo de capacidad

El Administrador dispondrá de:

**Administración → Infraestructura → Capacidad y Escalamiento**

El panel deberá mostrar como mínimo:

* Tier actual;
* capacidad autorizada;
* utilización actual;
* capacidad disponible;
* crecimiento;
* picos;
* proyección;
* Capacity Score;
* almacenamiento;
* procesamiento;
* estado de nodos;
* recomendaciones NEXUS;
* costos estimados cuando correspondan.

---

# 8. Human-Governed Automatic Scaling

FACT CENTRAL utilizará un modelo de:

**ESCALAMIENTO AUTOMÁTICO GOBERNADO POR ADMINISTRACIÓN**

NEXUS podrá:

1. detectar crecimiento;
2. proyectar necesidades;
3. calcular recursos;
4. calcular impacto;
5. generar recomendación;
6. solicitar autorización;
7. ejecutar cambios autorizados;
8. verificar resultados.

Ejemplo:

```text
Capacidad actual:
TIER 1

Utilización:
79 %

Proyección:
91 % en 30 días

Recomendación:
Migrar a TIER 2

[ APROBAR ]
[ POSPONER ]
[ MODIFICAR ]
```

---

# 9. Ventana de autorización

Las acciones técnicas previamente clasificadas como seguras podrán tener una ventana de aprobación administrativa.

Si el Administrador no responde dentro del tiempo configurado y existe riesgo operativo, NEXUS podrá ejecutar únicamente acciones de escalamiento previamente autorizadas por política.

Esto podrá incluir:

* aumentar workers;
* activar nodos disponibles;
* redistribuir trabajos;
* aumentar capacidad dentro de límites presupuestarios;
* aplicar backpressure.

No deberá utilizarse esta regla para conceder automáticamente privilegios sensibles, altas administrativas o permisos de seguridad.

**Escalamiento técnico y autorización de identidad son procesos diferentes.**

---

# 10. Separación entre adquisición y procesamiento

FACT CENTRAL nunca deberá depender de procesar un documento mientras todavía está siendo recibido.

Flujo obligatorio:

```text
GESTOR
   ↓
EDGE / CLOUDFLARE
   ↓
UPLOAD SERVICE
   ↓
ALMACENAMIENTO DURABLE
   ↓
INTEGRITY CHECK
   ↓
VERIFIED
   ↓
QUEUE
   ↓
PROCESSING
```

El procesamiento solamente comenzará después de confirmar la recepción íntegra del archivo.

---

# 11. Estados de adquisición

Todo archivo deberá pasar por estados controlados.

```text
CREATED
↓
UPLOADING
↓
RECEIVED
↓
INTEGRITY_CHECK
↓
VERIFIED
↓
QUEUED
↓
PROCESSING
↓
VALIDATING
↓
COMPLETED
```

Estados excepcionales:

```text
UPLOAD_INTERRUPTED
CORRUPTED
RETRY_PENDING
PROCESSING_FAILED
REVIEW_REQUIRED
```

Un archivo incompleto o corrupto jamás deberá ingresar al procesamiento normal.

---

# 12. Integridad

Cada archivo deberá disponer de mecanismos de verificación de integridad.

Podrá utilizarse SHA-256 u otro mecanismo aprobado.

```text
ARCHIVO ENVIADO
      ↓
   CHECKSUM
      ↓
ARCHIVO RECIBIDO
      ↓
   CHECKSUM
      ↓
  COMPARACIÓN
```

Si la integridad no puede confirmarse:

```text
CORRUPTED / INCOMPLETE
```

y el documento no será procesado.

---

# 13. Idempotencia

Toda operación crítica de adquisición deberá soportar idempotencia.

Si un cliente repite una solicitud porque perdió la respuesta de red, FACT CENTRAL deberá reconocer la operación original.

Una retransmisión no deberá generar automáticamente:

* doble documento;
* doble expediente;
* doble procesamiento;
* doble contabilización.

---

# 14. Cloudflare y protección de entrada

Cloudflare o el servicio Edge utilizado deberá proteger FACT CENTRAL sin convertir picos legítimos de actividad en pérdida documental.

Se distinguirá entre:

* tráfico anónimo;
* usuarios autenticados;
* gestores autenticados;
* API;
* servicio de uploads;
* servicios internos.

Los límites deberán poder establecerse por identidad, servicio y contexto.

Las políticas concretas deberán validarse contra las capacidades vigentes del proveedor antes de implementación.

---

# 15. Upload Service

Las cargas documentales deberán utilizar un servicio especializado.

Cuando sea técnicamente conveniente:

```text
CLIENTE
   ↓
Solicita Upload ID
   ↓
FACT CENTRAL
   ↓
TOKEN TEMPORAL
   ↓
ALMACENAMIENTO
```

Esto evitará que grandes archivos tengan que atravesar innecesariamente todos los procesos del backend principal.

---

# 16. Sistema de colas

La recepción y el procesamiento estarán desacoplados mediante colas persistentes.

Ejemplos:

```text
document.ingestion
document.validation
document.ocr
document.classification
document.extraction
document.duplicate_detection
document.association
expedient.processing
ai.reasoning
agent.execution
report.generation
```

Una carga de 20,000 documentos podrá generar 20,000 trabajos pendientes sin ejecutar 20,000 procesos simultáneamente.

---

# 17. Backpressure

Cuando la velocidad de entrada sea superior a la capacidad de procesamiento, FACT CENTRAL deberá controlar la carga.

NEXUS podrá:

* aumentar workers;
* activar nodos;
* redistribuir trabajos;
* reducir procesos secundarios;
* limitar temporalmente determinadas operaciones;
* informar retrasos;
* priorizar trabajos críticos.

La saturación de procesamiento no deberá provocar pérdida de documentos.

---

# 18. Procesamiento distribuido

FACT CENTRAL deberá soportar múltiples nodos de procesamiento.

Configuración mínima recomendada para alta disponibilidad:

```text
              QUEUE
            /       \
           ▼         ▼
         NODE A    NODE B
         VPS/PC    VPS/PC
```

Ambos podrán consumir trabajos de la misma infraestructura lógica.

La caída de un nodo no deberá detener todo el procesamiento.

---

# 19. Workers independientes

Los workers no deberán depender directamente unos de otros.

```text
QUEUE
 │
 ├── Worker 01
 ├── Worker 02
 ├── Worker 03
 └── Worker N
```

Agregar nuevos workers deberá aumentar capacidad sin modificar el algoritmo de negocio.

---

# 20. Nuevos nodos

Una nueva computadora o servidor podrá incorporarse como **FACT CENTRAL NODE**.

Proceso:

```text
NEW NODE
↓
REGISTER
↓
SECURITY CHECK
↓
ADMIN APPROVAL
↓
RESOURCE PROFILE
↓
NEXUS
↓
ROLE ASSIGNMENT
```

NEXUS podrá evaluar:

* CPU;
* RAM;
* GPU;
* SSD;
* red;
* disponibilidad;
* rendimiento.

Y recomendar funciones.

---

# 21. Funciones de los nodos

Un nodo podrá ejecutar una o varias funciones:

* API;
* procesamiento;
* OCR;
* IA;
* clasificación;
* validación;
* workers;
* almacenamiento;
* cache;
* réplica;
* backup.

La función deberá asignarse mediante configuración y no quedar codificada permanentemente para una máquina específica.

---

# 22. Escalamiento de API y backend

El aumento de usuarios no deberá requerir reescribir la API.

Se utilizará escalamiento horizontal.

```text
                 LOAD BALANCER
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
        API 1       API 2       API 3
```

Si aumenta la carga:

```text
API 4
API 5
...
API N
```

podrán incorporarse.

---

# 23. Connection Pool

Las conexiones de usuarios no deberán transformarse directamente en conexiones PostgreSQL.

```text
USUARIOS
   ↓
API
   ↓
CONNECTION POOL
   ↓
POSTGRESQL
```

El pool deberá controlar:

* conexiones máximas;
* conexiones disponibles;
* tiempos de espera;
* saturación;
* reutilización;
* errores.

---

# 24. APIs externas

Los servicios externos deberán estar protegidos mediante:

```text
QUEUE
↓
RATE LIMITER
↓
WORKERS
↓
EXTERNAL API
```

FACT CENTRAL respetará los límites de cada proveedor sin perder los trabajos pendientes.

---

# 25. Almacenamiento lógico

FACT CENTRAL no deberá depender directamente de unidades físicas como:

```text
D:\
E:\
F:\
```

La aplicación utilizará un **Storage Manager**.

FACT CENTRAL verá almacenamiento lógico:

```text
STORAGE_FACTCENTRAL
```

aunque físicamente existan múltiples dispositivos.

---

# 26. Storage Pool

Los dispositivos podrán formar parte de uno o varios Storage Pools.

Ejemplo:

```text
SSD A    1 TB
SSD B    2 TB
SSD C    2 TB
        ↓
STORAGE POOL
        ↓
CAPACIDAD LÓGICA
```

La aplicación no decidirá manualmente en qué SSD debe almacenarse cada documento.

Storage Manager realizará esta decisión.

---

# 27. Identidad independiente del disco

La identidad de un documento nunca deberá depender de su ubicación física.

No se utilizará como identidad:

```text
D:\FACTCENTRAL\factura.pdf
```

Se utilizará una identidad lógica:

```text
document_id
storage_key
checksum
```

Ejemplo:

```text
document_id:
DOC-938472

storage_key:
factcentral/2026/07/938472
```

---

# 28. Expansión de almacenamiento

NEXUS deberá observar:

* capacidad total;
* capacidad utilizada;
* capacidad libre;
* crecimiento diario;
* crecimiento mensual;
* velocidad de crecimiento;
* salud de discos;
* capacidad proyectada.

Estados conceptuales:

| Utilización | Estado                |
| ----------- | --------------------- |
| <60 %       | NORMAL                |
| 60–70 %     | SALUDABLE             |
| 70–80 %     | PLANIFICAR            |
| 80–90 %     | EXPANSIÓN RECOMENDADA |
| >90 %       | CRÍTICO               |

Estos valores serán configurables.

---

# 29. Forecasting de almacenamiento

NEXUS deberá predecir cuándo se alcanzarán determinados umbrales.

Ejemplo:

```text
Utilización actual: 73 %
Crecimiento: 8 % mensual

80 % estimado:
26 días

90 % estimado:
63 días
```

Administración recibirá una recomendación antes de alcanzar el límite.

---

# 30. Incorporación de nuevo almacenamiento

Un nuevo SSD, NAS o recurso de almacenamiento deberá pasar por:

```text
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

Una vez incorporado, Storage Manager podrá utilizarlo automáticamente.

FACT CENTRAL no deberá requerir modificaciones de código.

---

# 31. Distribución automática

Storage Manager decidirá dónde realizar nuevas escrituras considerando:

* espacio disponible;
* salud;
* rendimiento;
* latencia;
* tipo de almacenamiento;
* redundancia;
* carga.

Ejemplo:

```text
Storage A = 82 %
Storage B = 44 %
Storage C = 31 %

Nuevas escrituras:
priorizar B/C
```

---

# 32. Rebalanceo

El sistema deberá poder redistribuir datos cuando sea necesario.

Ejemplo:

```text
ANTES

A = 90 %
B = 10 %

REBALANCE

A = 50 %
B = 50 %
```

El movimiento físico no deberá cambiar la identidad del documento ni sus relaciones dentro del ERP.

---

# 33. SSD externos y USB

Los dispositivos externos podrán utilizarse para:

* backup;
* archivo;
* copia adicional;
* recuperación;
* transferencia controlada.

No deberán constituir por defecto el único almacenamiento primario operativo debido al riesgo de desconexión física.

---

# 34. Réplica no es backup

FACT CENTRAL distinguirá entre:

### REPLICA

Garantiza disponibilidad.

### BACKUP

Garantiza recuperación histórica.

Una eliminación accidental puede replicarse.

Por eso la existencia de réplicas no elimina la necesidad de backups.

---

# 35. Estrategia de disponibilidad documental

Como objetivo arquitectónico se buscará:

```text
STORAGE PRINCIPAL
       │
       ├─────────────┐
       ▼             ▼
REPLICA LOCAL   REPLICA REMOTA
       │             │
       └──────┬──────┘
              ▼
       BACKUP HISTÓRICO
```

Las copias críticas no deberán depender todas de una misma computadora, disco o ubicación física.

---

# 36. Nuevas PCs como capacidad adicional

Cada nueva instalación autorizada podrá aportar recursos al ecosistema.

Una nueva PC podrá convertirse en:

* Processing Node;
* OCR Node;
* AI Node;
* Storage Node;
* Replica Node;
* Backup Node;
* Cache Node.

NEXUS podrá recomendar su función según las características detectadas.

---

# 37. Node Manager

El panel administrativo deberá disponer de:

**Infraestructura → Nodos**

Ejemplo:

| Nodo    | Estado |  CPU |  RAM | Storage | Función              |
| ------- | ------ | ---: | ---: | ------: | -------------------- |
| VPS-01  | ONLINE | 38 % | 44 % |       — | Processing           |
| NODE-01 | ONLINE | 25 % | 31 % |    2 TB | Processing + Storage |
| NODE-02 | ONLINE | 12 % | 28 % |    1 TB | Processing           |
| NODE-03 | ONLINE |    — |    — |    2 TB | Replica              |

---

# 38. Capacity Score

NEXUS podrá generar un indicador agregado:

```text
100 = Excelente
80  = Saludable
60  = Atención
40  = Riesgo
20  = Crítico
```

El Capacity Score será una referencia ejecutiva.

Las decisiones técnicas deberán continuar utilizando las métricas individuales.

---

# 39. Degradación controlada

Cuando la infraestructura esté bajo presión:

### Prioridad crítica

* seguridad;
* autenticación;
* integridad;
* adquisición segura;
* persistencia;
* operaciones esenciales.

### Prioridad alta

* expedientes;
* procesamiento operativo;
* validaciones esenciales.

### Prioridad media

* OCR no urgente;
* clasificación secundaria.

### Prioridad baja

* reportes históricos;
* aprendizaje no urgente;
* analítica pesada.

FACT CENTRAL deberá degradarse ordenadamente antes de colapsar.

---

# 40. Pruebas obligatorias

La implementación deberá incluir:

* Load Test;
* Stress Test;
* Spike Test;
* Endurance Test;
* Recovery Test;
* Massive Ingestion Test;
* Storage Failure Test;
* Node Failure Test;
* Network Interruption Test;
* Queue Recovery Test.

---

# 41. Capacity Baseline

Las cifras reales de rendimiento se determinarán mediante pruebas.

Se registrará:

```text
Hardware
CPU
RAM
Storage
Network

Documentos/minuto
OCR páginas/minuto
API requests/segundo
Eventos/segundo
Usuarios concurrentes
Latencia
Tiempo de cola
```

Las mediciones reales sustituirán progresivamente las estimaciones iniciales.

---

# 42. Relación con Resource Engine

Capacity Planning responde:

> ¿CUÁNTA CAPACIDAD NECESITAMOS?

Resource Engine responde:

> ¿CÓMO UTILIZAMOS LOS RECURSOS DISPONIBLES?

---

# 43. Relación con Cost Model

`26D_INFRASTRUCTURE_COST_MODEL.md` deberá transformar necesidades de capacidad en impacto económico.

```text
CAPACIDAD
↓
RECURSOS
↓
COSTO
↓
DECISIÓN
```

---

# 44. Relación con System Health

`26E_SYSTEM_HEALTH_MODEL.md` deberá observar permanentemente:

* nodos;
* CPU;
* RAM;
* discos;
* almacenamiento;
* red;
* colas;
* bases de datos;
* APIs;
* workers;
* errores;
* latencia.

---

# 45. Relación con Autonomous Operations

`26F_AUTONOMOUS_OPERATIONS_CENTER.md` utilizará esta información para:

```text
DETECTAR
↓
PREDECIR
↓
RECOMENDAR
↓
SOLICITAR AUTORIZACIÓN
↓
EJECUTAR
↓
VERIFICAR
```

---

# 46. Principios arquitectónicos obligatorios

### PRINCIPIO 1

La escala será configuración, no lógica rígida.

### PRINCIPIO 2

La recepción y el procesamiento estarán desacoplados.

### PRINCIPIO 3

Nunca se procesará un archivo cuya integridad no esté confirmada.

### PRINCIPIO 4

La saturación de procesamiento no deberá implicar pérdida documental.

### PRINCIPIO 5

Los workers serán reemplazables y escalables.

### PRINCIPIO 6

La identidad del documento será independiente del disco físico.

### PRINCIPIO 7

Una nueva máquina podrá convertirse en recurso del ecosistema previa autorización.

### PRINCIPIO 8

La réplica garantiza disponibilidad; el backup garantiza recuperación.

### PRINCIPIO 9

NEXUS deberá anticipar el crecimiento antes de alcanzar los límites.

### PRINCIPIO 10

Administración conservará control sobre los cambios relevantes de capacidad y costo.

---

# 47. Regla de integridad crítica

> LA PÉRDIDA TEMPORAL DE CAPACIDAD DE PROCESAMIENTO JAMÁS DEBERÁ CONVERTIRSE EN PÉRDIDA, CORRUPCIÓN O PROCESAMIENTO PARCIAL DE INFORMACIÓN.

Si todos los nodos de procesamiento se encuentran temporalmente fuera de servicio, los documentos íntegramente recibidos deberán permanecer almacenados y pendientes hasta recuperar capacidad.

---

# 48. Regla de crecimiento

> FACT CENTRAL DEBERÁ CRECER MEDIANTE LA INCORPORACIÓN DE RECURSOS Y NO MEDIANTE LA REESCRITURA PERMANENTE DE SU LÓGICA.

El crecimiento normal deberá resolverse principalmente mediante:

```text
MÁS API NODES
MÁS WORKERS
MÁS PROCESSING NODES
MÁS STORAGE
MÁS REPLICAS
MAYOR CAPACIDAD DE BASE DE DATOS
```

manteniendo estable el núcleo funcional.

---

# 49. Arquitectura conceptual resultante

```text
                         INTERNET
                            │
                            ▼
                    CLOUDFLARE / EDGE
                            │
                            ▼
                      LOAD BALANCER
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
              API NODE A           API NODE B
                 │                     │
                 └──────────┬──────────┘
                            ▼
                      UPLOAD SERVICE
                            │
                            ▼
                    DURABLE STORAGE
                            │
                    INTEGRITY CHECK
                            │
                            ▼
                         QUEUE
                ┌───────────┼───────────┐
                ▼           ▼           ▼
              VPS 01      NODE 01     NODE 02
                │           │           │
                └───────────┼───────────┘
                            ▼
                      PROCESSING
                  OCR / IA / NEXUS
                            │
                            ▼
                       POSTGRESQL
                            │
                            ▼
                     STORAGE MANAGER
                  ┌─────────┼─────────┐
                  ▼         ▼         ▼
                SSD A     SSD B     STORAGE C
                  │
                  └─────────┬─────────┘
                            ▼
                         REPLICA
                            │
                            ▼
                     REMOTE BACKUP
```

---

# 50. Estado del documento

**CAPACITY PLANNING — ARQUITECTURA LÓGICA DEFINIDA**

Las capacidades numéricas de rendimiento de CPU, RAM, red, workers, PostgreSQL, OCR, IA y almacenamiento deberán calibrarse durante implementación mediante benchmarks y pruebas reales.

La arquitectura queda diseñada para que estas cifras puedan modificarse sin alterar las reglas fundamentales de FACT CENTRAL.
