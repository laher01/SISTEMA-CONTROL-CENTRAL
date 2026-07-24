26B — DISASTER RECOVERY PLAN
FACT CENTRAL
Plan Oficial de Recuperación ante Desastres de NEXUS

Versión: 2.0
Estado: Arquitectura lógica consolidada
Modelo: Recuperación distribuida, redundante y automatizable

1. Objetivo

Definir cómo FACT CENTRAL y NEXUS deberán responder, recuperarse y continuar operando frente a fallas técnicas, pérdida de infraestructura, corrupción de datos, indisponibilidad de servicios o desastres físicos.

Este documento establece los procedimientos lógicos para proteger:

documentos;
expedientes;
bases de datos;
configuraciones;
colas;
nodos;
almacenamiento;
réplicas;
backups;
servicios API;
componentes NEXUS.

La recuperación deberá priorizar la integridad de los datos sobre la velocidad de restauración.

2. Principio fundamental

FACT CENTRAL DEBERÁ ESTAR PREPARADO PARA FALLAR SIN PERDER SU HISTORIA.

Un fallo de:

una PC;
una VPS;
un SSD;
una conexión;
un worker;
PostgreSQL;
un servicio externo;
una ubicación física;

no deberá significar automáticamente pérdida irreversible de información.

3. Filosofía

La recuperación se basará en cinco principios:

DETECTAR
↓
AISLAR
↓
CONSERVAR
↓
RECUPERAR
↓
VERIFICAR

NEXUS deberá evitar acciones automáticas que puedan amplificar una corrupción o pérdida.

4. Prioridad de recuperación

El orden general será:

PRIORIDAD 1

Integridad y seguridad de la información.

PRIORIDAD 2

Acceso a documentos y expedientes.

PRIORIDAD 3

Base de datos.

PRIORIDAD 4

API y operaciones del ERP.

PRIORIDAD 5

Procesamiento OCR / IA.

PRIORIDAD 6

Analítica, reportes y procesos secundarios.

5. Clasificación de incidentes

Los eventos se clasificarán como:

Nivel 1 — Incidente menor

Ejemplos:

worker detenido;
proceso fallido;
error temporal;
disco con alta utilización.

El sistema continúa operando.

Nivel 2 — Degradación

Ejemplos:

caída de un Processing Node;
pérdida de una réplica;
API Node offline;
almacenamiento degradado.

Existe continuidad parcial o completa.

Nivel 3 — Falla crítica

Ejemplos:

PostgreSQL Primary offline;
pérdida del Storage Primary;
corrupción detectada;
caída de varios nodos.

Debe iniciarse failover o recuperación.

Nivel 4 — Desastre

Ejemplos:

pérdida de servidor principal;
pérdida completa de almacenamiento local;
daño físico de infraestructura;
incendio;
robo;
pérdida total de una ubicación.

Se activa recuperación mediante infraestructura remota y backups.

6. Objetivos RPO y RTO

FACT CENTRAL deberá manejar dos métricas.

RPO — Recovery Point Objective

Cantidad máxima aceptable de información que podría perderse entre el último estado seguro y el incidente.

RTO — Recovery Time Objective

Tiempo objetivo para recuperar el servicio.

Los valores definitivos deberán definirse por componente.

Ejemplo conceptual:

Componente	Prioridad	RPO	RTO
PostgreSQL	Crítica	Muy bajo	Muy bajo
Documentos originales	Crítica	Cercano a cero	Bajo
Cola	Alta	Bajo	Bajo
OCR	Media	Reprocesable	Medio
Reportes	Baja	Reprocesable	Alto
7. Regla de conservación del original

Todo documento recibido y verificado deberá conservarse antes de procesamiento.

Flujo:

UPLOAD
↓
DURABLE STORAGE
↓
CHECKSUM
↓
VERIFIED
↓
QUEUE
↓
PROCESSING

Si el procesamiento falla, el original seguirá disponible.

8. Recuperación de uploads interrumpidos

Si una conexión se corta durante adquisición:

UPLOADING
↓
UPLOAD_INTERRUPTED

El sistema deberá:

conservar fragmentos válidos si la tecnología lo permite;
permitir reanudación;
permitir reinicio;
evitar procesamiento incompleto.

Nunca deberá considerarse válido un archivo parcialmente recibido.

9. Recuperación de Processing Node

Si un nodo de procesamiento falla:

NODE A
OFFLINE

La cola deberá liberar o reprogramar sus trabajos no completados.

Otros nodos deberán poder continuar:

QUEUE
 ├── NODE B
 ├── NODE C
 └── NODE D

Los trabajos deberán ser idempotentes cuando sea posible.

10. Trabajo en estado incierto

Si un worker cae durante ejecución, el trabajo no deberá asumirse automáticamente como completado.

Estados posibles:

PROCESSING
↓
WORKER LOST
↓
RECOVERY_CHECK

Luego:

COMPLETED

si existe evidencia de finalización,

o:

RETRY_PENDING

si debe volver a ejecutarse.

11. Idempotencia en recuperación

Las operaciones de recuperación deberán evitar duplicaciones.

Una tarea repetida no deberá generar:

doble documento;
doble expediente;
doble pago;
doble contabilización.

La combinación de:

operation_id;
document_id;
checksum;
idempotency_key;

permitirá reconocer repeticiones.

12. Recuperación de API Node

Si un API Node falla:

API-02
OFFLINE

el Load Balancer deberá dejar de enviarle tráfico.

LOAD BALANCER
 ├── API-01
 └── API-03

La caída deberá ser transparente para la lógica de negocio siempre que existan nodos disponibles.

13. Recuperación de Load Balancer

La arquitectura deberá evitar, cuando la escala lo justifique, que el Load Balancer se convierta en un punto único de falla.

Las estrategias podrán incluir:

servicio gestionado;
instancia redundante;
failover;
configuración replicada.
14. Recuperación de Cloudflare / Edge

Si la capa Edge presenta problemas, FACT CENTRAL deberá contar con procedimientos documentados para:

identificar la falla;
conservar servicios internos;
activar ruta alternativa cuando corresponda;
evitar pérdida de uploads ya recibidos.

Cloudflare será protección y entrada, no repositorio de verdad.

15. Caída de Internet local

Si una oficina pierde Internet:

los nodos locales podrán continuar tareas internas que no requieran red externa;
las cargas nuevas podrán quedar pendientes localmente si se implementa modo offline;
al restablecer conexión se sincronizarán de manera controlada.

Ningún proceso de sincronización deberá generar duplicados.

16. Recuperación de PostgreSQL

PostgreSQL deberá contar con estrategia de:

PRIMARY
↓
REPLICA
↓
BACKUP

Ante falla del Primary:

PRIMARY OFFLINE
↓
VALIDATION
↓
PROMOTE REPLICA
↓
NEW PRIMARY

La promoción deberá verificarse antes de reanudar escrituras completas.

17. Protección contra corrupción lógica

Una réplica no protege por sí sola contra corrupción.

Si una operación incorrecta modifica datos:

PRIMARY
↓
CORRUPTION
↓
REPLICA

la corrupción puede propagarse.

Por eso deberán existir backups históricos independientes.

18. Point-in-Time Recovery

Cuando la infraestructura lo permita, PostgreSQL deberá soportar recuperación a un punto temporal anterior.

Ejemplo:

Incidente:
10:37

Estado válido:
10:34

El sistema podrá restaurar hasta el último punto seguro disponible.

19. Recuperación de Storage Primary

Si el Storage Primary falla:

STORAGE A
OFFLINE

Storage Manager deberá localizar una réplica válida.

STORAGE B
REPLICA VALID

La aplicación deberá continuar utilizando el mismo:

document_id
storage_key

aunque cambie la ubicación física.

20. Regla de independencia física

LA PÉRDIDA DE UN DISCO NO DEBERÁ CAMBIAR LA IDENTIDAD DEL DOCUMENTO.

Los documentos estarán vinculados a identificadores lógicos, no a rutas físicas rígidas.

21. Recuperación de un SSD

Cuando un disco falle:

SSD-02
FAILED

NEXUS deberá:

marcarlo como no disponible;
detener nuevas escrituras;
identificar objetos afectados;
verificar réplicas;
notificar;
solicitar reemplazo;
incorporar nuevo almacenamiento;
reconstruir redundancia.
22. Rebuilding de almacenamiento

Nuevo disco:

NEW STORAGE
↓
HEALTH CHECK
↓
ADMIN APPROVAL
↓
STORAGE POOL
↓
REPLICATION
↓
REBUILD
↓
HEALTHY

El proceso podrá ejecutarse en segundo plano sin detener el ERP.

23. Pérdida de Storage Pool completo

Si el pool local queda fuera de servicio:

LOCAL STORAGE
OFFLINE

FACT CENTRAL deberá recurrir a:

REMOTE REPLICA

o

BACKUP

según disponibilidad.

24. Réplica local

La réplica local protege contra:

falla de SSD;
falla de volumen;
falla de dispositivo.

No protege contra pérdida completa del lugar físico.

25. Réplica remota

La réplica remota deberá ubicarse en infraestructura físicamente independiente.

Puede ser:

otra sede;
VPS;
almacenamiento cloud;
datacenter.

Protege frente a pérdida completa del sitio principal.

26. Backup histórico

El backup histórico deberá permitir regresar a estados anteriores.

Deberá proteger contra:

borrado accidental;
corrupción;
errores humanos;
ransomware;
sincronización incorrecta;
pérdida de réplica.
27. Regla 3-2-1 como referencia

Como principio de protección podrá utilizarse:

3 COPIAS
2 MEDIOS O UBICACIONES DIFERENTES
1 COPIA REMOTA

La implementación exacta deberá adaptarse al presupuesto y escala.

28. Backups cifrados

Todos los backups críticos deberán almacenarse cifrados.

Las claves deberán gestionarse independientemente de los archivos respaldados.

29. Verificación de backups

Un backup no deberá considerarse válido solo porque exista un archivo.

Deberá verificarse periódicamente:

integridad;
lectura;
restauración;
checksum;
consistencia.
30. Pruebas de restauración

FACT CENTRAL deberá ejecutar pruebas periódicas.

Ejemplo:

BACKUP
↓
RESTORE TEST ENVIRONMENT
↓
VERIFY
↓
RESULT

Un backup que nunca se ha probado no deberá considerarse garantía de recuperación.

31. Recuperación de Redis / Cache

Redis o sistemas equivalentes no deberán contener la única copia de información crítica.

Si Redis falla:

REDIS OFFLINE

el sistema deberá reconstruir o recuperar:

cache;
sesiones;
estados temporales;

según diseño.

32. Recuperación de Queue

Las colas críticas deberán ser persistentes.

Ante reinicio:

QUEUE RESTART
↓
PENDING JOBS RESTORED

Los trabajos pendientes no deberán desaparecer por reinicio del servidor.

33. Dead Letter Queue

Trabajos que fallen repetidamente podrán pasar a:

DEAD LETTER QUEUE

Esto permitirá:

conservarlos;
analizarlos;
corregirlos;
reintentarlos.

Nunca deberán desaparecer silenciosamente.

34. Recuperación de Event Bus

Si el Event Bus está temporalmente fuera de servicio:

los eventos críticos deberán persistirse o reintentarse;
los productores no deberán perder información esencial;
los consumidores deberán poder retomar desde un punto conocido.
35. Recuperación de OCR

OCR será considerado reprocesable.

Si un worker OCR falla:

DOCUMENT ORIGINAL
EXISTS
↓
OCR RETRY

No será necesario recuperar un resultado temporal si puede regenerarse desde el original.

36. Recuperación de IA

Los resultados de IA podrán clasificarse como:

reproducibles;
persistentes;
críticos;
auxiliares.

La indisponibilidad de un proveedor IA no deberá impedir que FACT CENTRAL conserve los documentos.

37. Proveedores externos

Ante caída de:

SUNAT;
APIPERU;
OpenAI;
WhatsApp;
correo;
almacenamiento externo;

los trabajos deberán quedar:

EXTERNAL_SERVICE_PENDING

y reintentarse posteriormente.

38. Retry Policy

Los reintentos utilizarán:

número máximo;
espera progresiva;
jitter;
registro;
escalamiento.

Ejemplo:

1 minuto
5 minutos
15 minutos
1 hora

La política concreta dependerá del servicio.

39. Circuit Breaker

Cuando un proveedor externo falle repetidamente:

SERVICE FAILING
↓
CIRCUIT OPEN

FACT CENTRAL dejará de bombardearlo temporalmente.

Luego:

PROBE
↓
SERVICE HEALTHY
↓
CIRCUIT CLOSED
40. Disaster Recovery por ubicación

Escenario:

SEDE PRINCIPAL
OFFLINE

La arquitectura deberá permitir continuar desde:

VPS
REMOTE STORAGE
REMOTE DATABASE

según el nivel de implementación disponible.

41. Pérdida total de oficina

En caso de:

robo;
incendio;
inundación;
daño eléctrico;

la recuperación no deberá depender de dispositivos dentro de la misma oficina.

Debe existir al menos una copia remota de la información crítica.

42. Nuevas PCs como nodos de recuperación

Una nueva PC autorizada podrá incorporarse durante recuperación.

Ejemplo:

PC NUEVA
↓
FACT CENTRAL NODE
↓
REGISTER
↓
SECURITY CHECK
↓
ADMIN APPROVAL
↓
RESTORE CONFIG
↓
PROCESSING NODE

Esto permitirá reconstruir capacidad rápidamente.

43. Configuración como código

Siempre que sea posible, la configuración de infraestructura deberá mantenerse documentada y reproducible.

Objetivo:

SERVIDOR PERDIDO
↓
NEW SERVER
↓
DEPLOY CONFIGURATION
↓
NODE RESTORED

y no depender de configuraciones manuales desconocidas.

44. Secrets Recovery

Las credenciales críticas deberán contar con procedimientos separados de recuperación.

Nunca deberán almacenarse en:

código fuente;
repositorios públicos;
archivos sin cifrado.
45. Registro de incidentes

Todo incidente deberá generar:

incident_id
fecha
hora
componente
tipo
severidad
causa
impacto
acciones
resultado
duración
datos afectados
46. Timeline del incidente

NEXUS deberá reconstruir:

10:31 WARNING
10:34 NODE DEGRADED
10:36 NODE OFFLINE
10:36 FAILOVER STARTED
10:37 NODE B ACTIVE
10:39 SERVICE STABLE

Esto permitirá auditoría y aprendizaje.

47. Automated Recovery

NEXUS podrá ejecutar automáticamente acciones previamente autorizadas.

Ejemplos:

reiniciar worker;
mover trabajos;
sacar nodo del balanceo;
activar réplica;
redistribuir procesamiento;
bloquear almacenamiento defectuoso.
48. Human-Governed Recovery

Las acciones de mayor impacto requerirán autorización administrativa.

Ejemplos:

restaurar backup histórico;
promover una base no verificada;
eliminar datos;
cambiar infraestructura principal;
reconstruir almacenamiento masivo.
49. Escalamiento de emergencia

Ante falla múltiple:

CAPACITY LOSS
↓
EMERGENCY MODE

NEXUS podrá priorizar:

adquisición;
integridad;
base de datos;
expedientes;
operaciones críticas.

OCR, IA, reportes y procesos secundarios podrán detenerse temporalmente.

50. Modo seguro

Cuando exista incertidumbre sobre integridad:

SAFE MODE

Podrá:

permitir lectura;
bloquear escrituras;
suspender procesamiento;
conservar uploads;
requerir revisión administrativa.
51. Protección contra propagación de corrupción

Si se detecta posible corrupción:

SUSPECT DATA
↓
ISOLATE
↓
STOP REPLICATION IF NEEDED
↓
VERIFY

No deberá propagarse automáticamente a todas las réplicas.

52. Checksum documental

Los documentos deberán poder verificarse mediante checksum.

Esto permitirá detectar:

modificación;
corrupción;
transferencia incompleta.
53. Inventario de recuperación

NEXUS deberá conocer:

NODOS
STORAGE
REPLICAS
BACKUPS
DATABASES
QUEUES
SERVICES

y su estado actual.

54. Disaster Recovery Dashboard

El Administrador deberá disponer de:

Administración → Infraestructura → Recuperación

Podrá mostrar:

Estado general
Último backup
Última verificación
Réplicas
RPO
RTO
Incidentes
Nodos disponibles
Storage disponible
Acciones recomendadas
55. Indicadores

Ejemplos:

Backup Health
Replication Health
Recovery Readiness
Storage Redundancy
Node Redundancy
Database Redundancy
56. Recovery Readiness Score

NEXUS podrá calcular un indicador:

100 = preparado
80  = saludable
60  = atención
40  = riesgo
20  = crítico
57. Simulaciones

El sistema deberá permitir ejercicios de recuperación.

Ejemplos:

SIMULAR FALLA NODE
SIMULAR FALLA STORAGE
SIMULAR FALLA DB
SIMULAR PÉRDIDA DE SEDE

Preferentemente en ambientes controlados.

58. Pruebas obligatorias

Deberán realizarse:

Node Failure Test;
API Failover Test;
Database Failover Test;
Storage Failure Test;
Backup Restore Test;
Queue Recovery Test;
Network Failure Test;
Remote Recovery Test;
Full Site Disaster Test.
59. Recuperación de una PC

La pérdida de una PC de trabajo no deberá afectar el sistema central.

Una nueva PC deberá poder:

INSTALL
↓
AUTHENTICATE
↓
REGISTER
↓
RESTORE PROFILE
↓
CONTINUE
60. Recuperación de un Processing Node

Los Processing Nodes deberán ser reemplazables.

No almacenarán la única copia de información crítica.

Su pérdida deberá resolverse agregando o activando otro nodo.

61. Recuperación de Storage Node

Los Storage Nodes deberán mantener redundancia suficiente según su función.

Un Storage Node sin réplica deberá considerarse riesgo operativo.

62. Recuperación del sistema completo

En un escenario extremo:

LOCAL INFRASTRUCTURE LOST

la recuperación será:

REMOTE BACKUP
↓
NEW INFRASTRUCTURE
↓
RESTORE DATABASE
↓
RESTORE STORAGE
↓
RESTORE CONFIG
↓
VERIFY
↓
START API
↓
START QUEUE
↓
START PROCESSING
↓
VALIDATE
↓
PRODUCTION
63. Orden de restauración

Orden recomendado:

1 SECURITY / SECRETS
2 NETWORK
3 STORAGE
4 DATABASE
5 QUEUE / EVENT SYSTEM
6 API
7 NEXUS CORE
8 PROCESSING
9 OCR / IA
10 REPORTING / ANALYTICS
64. Validación posterior

Después de recuperación deberán verificarse:

checksum;
cantidad de documentos;
expedientes;
relaciones;
colas;
estados;
consistencia DB;
permisos;
auditoría.
65. No reanudar sin verificación

Una recuperación no deberá considerarse terminada simplemente porque el servidor inició.

Debe comprobarse:

SYSTEM STARTED
≠
SYSTEM HEALTHY
66. Postmortem

Todo incidente importante deberá generar un análisis posterior.

Debe responder:

qué ocurrió;
por qué ocurrió;
qué falló;
qué funcionó;
cuánto duró;
qué datos estuvieron en riesgo;
qué debe cambiar.
67. Aprendizaje NEXUS

Los incidentes podrán alimentar:

10_CONTINUOUS_LEARNING_SYSTEM.md

para mejorar:

alertas;
umbrales;
políticas;
recuperación;
capacidad.
68. Relación con Infrastructure Topology

26A_INFRASTRUCTURE_TOPOLOGY.md define:

QUÉ COMPONENTES EXISTEN Y CÓMO SE CONECTAN.

Este documento define:

QUÉ HACER CUANDO ESOS COMPONENTES FALLAN.

69. Relación con Capacity Planning

26C_CAPACITY_PLANNING.md determina capacidad y redundancia necesarias.

Disaster Recovery utiliza esa capacidad para determinar qué recursos de reemplazo deben existir.

70. Relación con System Health

26E_SYSTEM_HEALTH_MODEL.md deberá detectar señales tempranas de fallo.

DEGRADATION
↓
ALERT
↓
RECOVERY ACTION
71. Relación con Autonomous Operations

26F_AUTONOMOUS_OPERATIONS_CENTER.md coordinará las acciones automáticas de:

failover;
aislamiento;
recuperación;
redistribución;
alertas.
72. Reglas supremas
Regla 1

EL ORIGINAL VERIFICADO DE UN DOCUMENTO DEBERÁ SOBREVIVIR AL FALLO DE SU PROCESAMIENTO.

Regla 2

UNA RÉPLICA NO SUSTITUYE A UN BACKUP.

Regla 3

NINGÚN NODO DE PROCESAMIENTO DEBERÁ CONTENER LA ÚNICA COPIA DE INFORMACIÓN CRÍTICA.

Regla 4

LA RECUPERACIÓN DEBERÁ PRESERVAR IDENTIDAD, INTEGRIDAD Y TRAZABILIDAD.

Regla 5

ANTE DUDA SOBRE INTEGRIDAD, FACT CENTRAL DEBERÁ DETENER ESCRITURAS ANTES QUE ARRIESGAR CORRUPCIÓN.

Regla 6

LA PÉRDIDA DE UNA UBICACIÓN FÍSICA NO DEBERÁ SIGNIFICAR LA PÉRDIDA TOTAL DE FACT CENTRAL.

73. Arquitectura conceptual de recuperación
                    INCIDENTE
                       │
                       ▼
                   DETECCIÓN
                       │
                       ▼
                  CLASIFICACIÓN
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
            NODE     STORAGE    DB
             │          │        │
             ▼          ▼        ▼
          FAILOVER   REPLICA   REPLICA
             │          │        │
             └──────────┼────────┘
                        ▼
                     VERIFY
                        │
                ┌───────┴───────┐
                ▼               ▼
            HEALTHY          NOT HEALTHY
                │               │
                ▼               ▼
           RESUME OPS        BACKUP
                                │
                                ▼
                             RESTORE
                                │
                                ▼
                             VERIFY
74. Estado del documento

DISASTER RECOVERY PLAN — ARQUITECTURA LÓGICA DEFINIDA

Los tiempos exactos de RPO, RTO, frecuencia de backups, tecnología de replicación y automatización deberán calibrarse durante implementación y pruebas reales.

La arquitectura queda diseñada para permitir recuperación desde fallas individuales hasta pérdida total de infraestructura local.
