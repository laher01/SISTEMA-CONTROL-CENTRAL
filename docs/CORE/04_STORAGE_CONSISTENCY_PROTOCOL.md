# 04_STORAGE_CONSISTENCY_PROTOCOL.md

# FACT CENTRAL SaaS

## STORAGE CONSISTENCY PROTOCOL

Versión 1.0

---

# 1. Objetivo

Definir el protocolo oficial de consistencia de almacenamiento
de FACT CENTRAL.

Este documento establece:

- cómo se escriben los archivos;
- cómo se confirman;
- cómo se replican;
- cómo se mueven;
- cómo se validan;
- cómo se recuperan;
- cómo se evita la corrupción;
- cómo se resuelven escrituras concurrentes;
- cómo se controla el rebalanceo;
- cómo se conserva la integridad entre PostgreSQL y Storage;
- cómo se auditan todas las operaciones.

---

# 2. Principio fundamental

Ningún archivo deberá considerarse seguro únicamente porque
fue escrito en un disco.

Un archivo será considerado persistido cuando:

- el objeto haya sido escrito completamente;
- su hash coincida;
- su metadata haya sido registrada;
- exista una ubicación válida;
- se cumpla el nivel de réplica exigido;
- el estado haya sido confirmado de forma atómica;
- exista trazabilidad suficiente para recuperarlo.

---

# 3. Separación de responsabilidades

FACT CENTRAL distinguirá:

## PostgreSQL

Fuente oficial de:

- identidad;
- relaciones;
- Tenant;
- metadata;
- versión;
- estado;
- ubicaciones;
- hashes;
- réplicas;
- auditoría.

## Object Storage

Contiene los archivos digitales.

## Storage Manager

Decide:

- dónde escribir;
- dónde replicar;
- cuándo mover;
- cuándo reparar;
- cuándo archivar.

## Storage Node

Ejecuta operaciones físicas de almacenamiento.

## Backup System

Conserva copias históricas y de recuperación.

## Workflow Engine

Coordina procesos complejos.

## Event Bus

Transporta eventos.

## Rule Engine

Decide políticas aplicables.

---

# 4. Regla de autoridad

PostgreSQL será la fuente de verdad sobre:

- qué archivo existe;
- a qué Tenant pertenece;
- qué versión está vigente;
- dónde está almacenado;
- cuántas réplicas existen;
- cuál es su hash;
- qué ubicaciones están activas;
- cuál es su estado.

El Storage por sí solo no define la identidad del documento.

---

# 5. Entidades principales

El protocolo deberá manejar como mínimo:

- file_object;
- file_version;
- storage_location;
- storage_replica;
- storage_operation;
- storage_lock;
- storage_integrity_check;
- storage_rebalance_job;
- storage_repair_job;
- storage_policy;
- backup_reference;
- audit_event.

---

# 6. Identidad del archivo

Cada archivo tendrá:

- file_id;
- tenant_id;
- hash;
- size;
- mime_type;
- original_filename;
- normalized_filename;
- version;
- state;
- primary_location_id;
- created_at;
- verified_at;
- retention_policy;
- encryption_status.

El nombre del archivo no será su identidad técnica.

---

# 7. Estados oficiales del File Object

## PENDING_WRITE

Esperando escritura.

## WRITING

Escritura en progreso.

## WRITTEN_UNVERIFIED

Escrito, pendiente de verificación.

## VERIFIED

Hash y tamaño confirmados.

## REPLICATING

Generando réplicas.

## AVAILABLE

Disponible para uso.

## MOVING

En movimiento controlado.

## REBALANCING

Participando en rebalanceo.

## DEGRADED

Disponible, pero con menos réplicas de las requeridas.

## CORRUPTED

Contenido inconsistente o dañado.

## REPAIRING

En reparación.

## ARCHIVED

Movido a almacenamiento histórico.

## RESTORING

En recuperación.

## DELETED_LOGICAL

Eliminado lógicamente.

## DELETION_PENDING

Pendiente de eliminación física autorizada.

## DELETED_PHYSICAL

Eliminado físicamente según política.

---

# 8. Estados de una réplica

Cada réplica podrá estar en:

```text
CREATED
WRITING
WRITTEN_UNVERIFIED
VERIFIED
ACTIVE
DEGRADED
CORRUPTED
REPAIRING
RETIRED
DELETED
```

---

# 9. Política de almacenamiento

Cada Tenant o Plan podrá tener una política.

Ejemplo:

```text
HOT_STORAGE_REPLICAS = 2
BACKUP_COPIES = 1
OFFSITE_COPY = 1
IMMUTABLE_RETENTION = 30 días
```

La política deberá definir:

- número mínimo de réplicas;
- tipo de almacenamiento;
- región;
- retención;
- cifrado;
- disponibilidad;
- prioridad;
- restauración;
- costo máximo.

---

# 10. Escritura inicial

Flujo:

```text
RECEIVED_VERIFIED
      ↓
CREATE STORAGE OPERATION
      ↓
SELECT TARGET NODE
      ↓
WRITE TEMPORARY OBJECT
      ↓
VERIFY SIZE
      ↓
VERIFY HASH
      ↓
PROMOTE TO FINAL OBJECT
      ↓
REGISTER LOCATION
      ↓
COMMIT METADATA
      ↓
AVAILABLE
```

---

# 11. Escritura temporal

Los archivos no deberán escribirse directamente
como objetos definitivos.

Se utilizará una ubicación temporal:

```text
tenant/tmp/operation_id/...
```

Solo después de verificar se promoverá a:

```text
tenant/files/file_id/version/...
```

---

# 12. Promoción atómica

La transición de temporal a definitivo deberá ser atómica
o simular atomicidad mediante un protocolo controlado.

No deberá existir un momento en el que:

- PostgreSQL diga AVAILABLE;
- pero el archivo definitivo no exista.

---

# 13. Confirmación de escritura

Antes de confirmar:

```text
AVAILABLE
```

se deberá verificar:

- archivo completo;
- tamaño;
- hash;
- ubicación;
- permisos;
- Tenant;
- versión;
- réplica mínima;
- metadata.

---

# 14. Atomicidad entre PostgreSQL y Storage

Como PostgreSQL y Storage son sistemas diferentes,
no existe una transacción única nativa entre ambos.

Por ello se utilizará un patrón de confirmación controlada.

Flujo:

```text
1. Crear storage_operation = PENDING
2. Escribir objeto temporal
3. Verificar objeto
4. Registrar ubicación candidata
5. Marcar operación READY_TO_COMMIT
6. Promover objeto
7. Confirmar ubicación ACTIVE
8. Marcar File Object AVAILABLE
9. Publicar evento
```

Si cualquier paso falla,
el sistema retomará desde el último estado persistido.

---

# 15. Outbox Pattern

Los eventos derivados de una operación de Storage
deberán utilizar un mecanismo transaccional tipo Outbox.

Ejemplo:

```text
PostgreSQL:
- actualiza estado del archivo;
- registra evento pendiente;

Worker:
- publica evento;
- marca evento como enviado.
```

Así se evita:

```text
archivo confirmado
pero evento perdido
```

---

# 16. Idempotencia

Toda operación deberá tener:

- operation_id;
- idempotency_key;
- file_id;
- tenant_id;
- operation_type;
- source_location;
- target_location;
- state.

Repetir una operación no deberá:

- crear múltiples archivos;
- sobrescribir otra versión;
- duplicar réplicas;
- perder metadata.

---

# 17. Escritura concurrente

Si dos procesos intentan escribir el mismo file_id:

```text
SOLO UNO PODRÁ ADQUIRIR EL LOCK
```

El otro deberá:

- esperar;
- detectar operación existente;
- devolver resultado previo;
- o abortar de forma segura.

---

# 18. Locks distribuidos

Los locks deberán proteger operaciones como:

- escritura final;
- movimiento;
- rebalanceo;
- reparación;
- eliminación física;
- restauración;
- cambio de versión.

Los locks deberán ser:

- limitados por tiempo;
- renovables;
- auditables;
- identificables por propietario;
- recuperables tras caída.

---

# 19. Fuente del Lock

Los locks críticos no deberán depender únicamente
de memoria local.

Podrán persistirse en:

- PostgreSQL;
- servicio de coordinación;
- mecanismo distribuido autorizado.

La selección técnica concreta se definirá en implementación.

---

# 20. Lock por archivo

Clave conceptual:

```text
tenant_id
+
file_id
+
operation_type
```

Ejemplo:

```text
FC-A7K92M:DOC-123:MOVE
```

---

# 21. Expiración de Lock

Un lock deberá tener:

- created_at;
- expires_at;
- heartbeat;
- owner_id;
- operation_id.

Si el proceso muere:

- el lock expira;
- otra instancia puede recuperarlo;
- la operación se reevalúa antes de continuar.

---

# 22. Prohibición de sobrescritura silenciosa

Una versión verificada no deberá sobrescribirse
con contenido distinto.

Si cambia el contenido:

```text
NUEVA VERSIÓN
```

o:

```text
CONFLICTO
```

Nunca:

```text
REEMPLAZO SILENCIOSO
```

---

# 23. Versionado de archivos

Cada versión deberá conservar:

- file_version_id;
- parent_file_id;
- version_number;
- hash;
- size;
- created_at;
- created_by;
- reason;
- state;
- locations.

---

# 24. Archivo original

El archivo original recibido deberá conservarse.

Los derivados serán:

- miniaturas;
- OCR text;
- páginas separadas;
- PDF normalizado;
- imágenes;
- previews;
- compresiones.

Los derivados no reemplazan el original.

---

# 25. Réplicas

Una réplica es una copia física adicional
del mismo contenido.

Toda réplica deberá conservar:

- mismo file_id;
- mismo version_id;
- mismo hash;
- mismo tamaño;
- Tenant;
- ubicación distinta;
- estado;
- fecha de verificación.

---

# 26. Tipos de réplica

## HOT REPLICA

Disponible para lectura inmediata.

## WARM REPLICA

Disponible con pequeño retraso.

## COLD COPY

Archivada para recuperación.

## OFFSITE COPY

Ubicada fuera del sitio principal.

## IMMUTABLE COPY

No modificable durante su retención.

---

# 27. Regla mínima de disponibilidad

Un archivo podrá estar AVAILABLE cuando cumpla
la política mínima.

Ejemplo:

```text
1 copia primaria verificada
+
1 réplica verificada
```

Si pierde una réplica:

```text
DEGRADED
```

pero puede seguir disponible.

---

# 28. Estado DEGRADED

DEGRADED significa:

- el archivo todavía existe;
- al menos una copia es válida;
- no cumple la política ideal;
- debe repararse.

El sistema deberá crear:

```text
STORAGE_REPAIR_JOB
```

---

# 29. Verificación de réplicas

Toda réplica deberá validarse por:

- tamaño;
- hash;
- metadata;
- acceso;
- Tenant;
- versión.

---

# 30. Lectura

Una lectura deberá:

1. validar Tenant;
2. validar permiso;
3. seleccionar réplica activa;
4. verificar disponibilidad;
5. generar enlace temporal;
6. registrar acceso cuando corresponda.

---

# 31. Selección de réplica

La lectura podrá priorizar:

- nodo más cercano;
- menor latencia;
- réplica saludable;
- región;
- costo;
- disponibilidad.

Nunca deberá elegir una réplica:

- corrupta;
- incompleta;
- en escritura;
- no verificada;
- de otro Tenant.

---

# 32. Read-after-write

Después de confirmar AVAILABLE,
el sistema deberá garantizar que la lectura
pueda encontrar al menos una copia válida.

---

# 33. Lectura durante replicación

Si el archivo está REPLICATING,
la lectura podrá usar la primaria verificada.

La réplica incompleta no será elegible.

---

# 34. Movimiento

Mover un archivo no significa:

```text
cortar de origen
y luego pegar en destino
```

El flujo correcto será:

```text
LOCK
↓
COPIAR A DESTINO
↓
VALIDAR HASH
↓
REGISTRAR DESTINO
↓
ACTIVAR DESTINO
↓
MANTENER ORIGEN
↓
ACTUALIZAR PRIMARY
↓
RETIRAR ORIGEN SEGÚN POLÍTICA
↓
UNLOCK
```

---

# 35. Regla de Move

Todo movimiento deberá implementarse como:

```text
COPY
+
VERIFY
+
SWITCH
+
RETIRE
```

No como:

```text
DELETE
+
COPY
```

---

# 36. Movimiento atómico lógico

El cambio de ubicación primaria deberá realizarse
mediante actualización atómica en PostgreSQL.

Hasta confirmar el destino:

```text
origen sigue siendo válido
```

---

# 37. Fallo durante movimiento

Si falla antes de verificar destino:

- origen permanece activo;
- destino incompleto se elimina o marca inválido;
- operación queda FAILED o RETRYING.

Si falla después de verificar destino
pero antes de cambiar primaria:

- ambas copias pueden existir;
- PostgreSQL decide cuál está activa;
- el proceso se retoma.

Si falla después de activar destino:

- se valida origen;
- se completa retiro según política.

---

# 38. Rebalanceo

El rebalanceo distribuirá capacidad entre nodos.

Puede activarse por:

- uso de disco;
- costo;
- latencia;
- degradación;
- retiro de nodo;
- crecimiento;
- política.

---

# 39. Rebalanceo controlado

Flujo:

```text
DETECTAR DESBALANCE
↓
CALCULAR PLAN
↓
SIMULAR IMPACTO
↓
APROBAR SI CORRESPONDE
↓
RESERVAR CAPACIDAD
↓
MOVER POR LOTES
↓
VALIDAR CADA ARCHIVO
↓
ACTUALIZAR MÉTRICAS
↓
FINALIZAR
```

---

# 40. Rebalanceo por lotes

No se deberán mover todos los archivos simultáneamente.

Se usarán lotes con:

- tamaño máximo;
- concurrencia;
- prioridad;
- pausas;
- backpressure;
- rollback lógico.

---

# 41. Escritura durante rebalanceo

Si un nodo está recibiendo archivos nuevos
mientras participa en rebalanceo:

- el Storage Manager recalculará capacidad;
- las nuevas escrituras usarán la política vigente;
- no se escribirán en objetos bloqueados;
- no se moverá un archivo en escritura.

---

# 42. Archivo en movimiento

Mientras un archivo está MOVING:

- la lectura usa la copia activa;
- la escritura de nueva versión crea otra versión;
- la eliminación queda bloqueada;
- otro movimiento queda bloqueado;
- la reparación se coordina.

---

# 43. Reserva de capacidad

Antes de mover o replicar,
el destino deberá reservar capacidad.

La reserva evitará:

- llenar el nodo a mitad de transferencia;
- competir con otras operaciones;
- sobreasignación.

---

# 44. Capacidad mínima libre

Cada nodo deberá conservar un margen.

Ejemplo conceptual:

```text
WARNING = 70 %
HIGH = 80 %
CRITICAL = 90 %
EMERGENCY = 95 %
```

Los valores serán configurables.

---

# 45. Escritura en nodo crítico

Un nodo en estado CRITICAL no deberá recibir
nuevas escrituras normales.

Podrá:

- permitir recuperación;
- permitir operación de emergencia;
- mover datos fuera;
- quedar en solo lectura.

---

# 46. Storage Pool

El Storage Pool representa capacidad lógica agregada.

Ejemplo:

```text
SSD A
+
SSD B
+
NAS
+
Object Storage
```

El sistema no deberá tratar la suma bruta
como capacidad totalmente utilizable.

Debe descontar:

- réplicas;
- backups;
- margen libre;
- temporales;
- overhead;
- reservas.

---

# 47. Capacidad útil

Conceptualmente:

```text
CAPACIDAD ÚTIL
=
CAPACIDAD BRUTA
-
RÉPLICAS
-
BACKUPS
-
RESERVA
-
TEMPORALES
-
OVERHEAD
```

---

# 48. Storage Multiplication Factor

El factor deberá considerar:

- original;
- réplicas;
- backup;
- derivados;
- miniaturas;
- OCR;
- metadata;
- temporales.

Ejemplo conceptual:

```text
1 TB productivo
× factor 3
=
3 TB requeridos
```

El factor real deberá medirse y ajustarse.

---

# 49. Tipos de nodos

Un nodo podrá ser:

- LOCAL_SSD;
- LOCAL_HDD;
- NAS;
- VPS_STORAGE;
- OBJECT_STORAGE;
- CLOUD_ARCHIVE;
- OFFSITE_BACKUP;
- IMMUTABLE_BACKUP.

---

# 50. Salud del nodo

Cada nodo tendrá:

- ONLINE;
- DEGRADED;
- READ_ONLY;
- DRAINING;
- OFFLINE;
- QUARANTINED;
- FAILED;
- RETIRED.

---

# 51. Nodo DRAINING

DRAINING significa:

- no recibe nuevas escrituras;
- conserva lecturas;
- mueve datos hacia otros nodos;
- se prepara para retiro o mantenimiento.

---

# 52. Nodo READ_ONLY

READ_ONLY significa:

- permite lectura;
- no permite nueva escritura;
- no permite modificación;
- puede utilizarse para recuperación.

---

# 53. Nodo QUARANTINED

Un nodo sospechoso deberá aislarse.

Puede ocurrir por:

- malware;
- corrupción;
- acceso no autorizado;
- procesos desconocidos;
- inconsistencia de hashes;
- comportamiento anómalo.

---

# 54. Reparación

Cuando una réplica falla:

```text
DETECTAR
↓
MARCAR CORRUPTED
↓
SELECCIONAR COPIA SANA
↓
CREAR NUEVA RÉPLICA
↓
VALIDAR
↓
ACTIVAR
↓
RETIRAR COPIA DAÑADA
```

---

# 55. Fuente de reparación

La reparación deberá usar:

- réplica sana;
- backup verificado;
- copia inmutable;
- archivo original disponible.

No deberá reconstruirse desde datos no confiables.

---

# 56. Scrubbing

El sistema deberá realizar revisiones periódicas de integridad.

Proceso:

```text
SELECCIONAR MUESTRA O TOTAL
↓
RECALCULAR HASH
↓
COMPARAR
↓
MARCAR RESULTADO
↓
REPARAR SI CORRESPONDE
```

---

# 57. Frecuencia de Scrubbing

Podrá depender de:

- criticidad;
- Plan;
- edad;
- almacenamiento;
- riesgo;
- historial de fallos.

---

# 58. Corrupción

Se considera corrupción cuando:

- hash no coincide;
- tamaño no coincide;
- lectura falla;
- objeto incompleto;
- metadata incompatible;
- versión incorrecta.

---

# 59. Respuesta ante corrupción

El sistema deberá:

- aislar la copia;
- impedir lecturas desde ella;
- crear alerta;
- iniciar reparación;
- verificar otras réplicas;
- auditar el incidente.

---

# 60. Eliminación lógica

Por defecto:

```text
DELETE
=
DELETED_LOGICAL
```

El archivo deja de aparecer al Usuario,
pero no se borra físicamente de inmediato.

---

# 61. Eliminación física

Solo podrá ocurrir cuando:

- la retención terminó;
- no existe obligación legal;
- no existe bloqueo;
- no existe auditoría pendiente;
- no pertenece a un periodo protegido;
- existe autorización;
- se registró el evento.

---

# 62. Legal Hold

Un archivo podrá quedar bajo:

```text
LEGAL_HOLD
```

Mientras esté activo:

- no se elimina;
- no se modifica;
- no se archiva de forma incompatible;
- no se reduce su retención.

---

# 63. Backups inmutables

Las copias inmutables no podrán:

- sobrescribirse;
- eliminarse antes de retención;
- alterarse desde la API normal;
- borrarse por un nodo comprometido.

---

# 64. Separación de credenciales

La API normal no deberá tener permisos para:

- eliminar backups;
- cambiar retención inmutable;
- administrar Storage global;
- borrar réplicas externas.

---

# 65. Restauración

Flujo:

```text
SOLICITUD DE RESTAURACIÓN
↓
VALIDAR PERMISO
↓
LOCALIZAR COPIA
↓
VERIFICAR HASH
↓
CREAR NUEVA UBICACIÓN
↓
REGISTRAR VERSIÓN
↓
ACTIVAR
↓
AUDITAR
```

---

# 66. Restauración de Tenant

Una restauración deberá respetar:

- tenant_id;
- relaciones;
- versiones;
- permisos;
- fechas;
- consistencia con PostgreSQL.

No deberá mezclar Tenants.

---

# 67. Restauración puntual

Podrá restaurarse:

- un archivo;
- una versión;
- un Expediente;
- un periodo;
- un Tenant;
- un nodo.

---

# 68. Consistencia con PostgreSQL

Después de una restauración deberá comprobarse:

- toda ubicación apunta a objeto existente;
- todo objeto activo tiene metadata;
- todo hash coincide;
- todas las relaciones son válidas;
- no existen referencias huérfanas.

---

# 69. Reconciliación Storage-Database

Proceso periódico:

```text
POSTGRESQL
↓
LISTA DE OBJETOS ESPERADOS
↓
STORAGE
↓
OBJETOS REALES
↓
COMPARAR
```

Resultados:

```text
MATCHED
MISSING_OBJECT
ORPHAN_OBJECT
HASH_MISMATCH
METADATA_MISMATCH
DUPLICATE_LOCATION
```

---

# 70. Objeto huérfano

Un objeto existe en Storage,
pero no tiene referencia válida en PostgreSQL.

No deberá borrarse automáticamente.

Debe:

- aislarse;
- investigarse;
- relacionarse si corresponde;
- eliminarse solo por política autorizada.

---

# 71. Referencia rota

PostgreSQL apunta a un objeto inexistente.

Resultado:

```text
MISSING_OBJECT
```

El sistema deberá:

- buscar réplica;
- buscar backup;
- restaurar;
- alertar;
- evitar devolver enlace roto.

---

# 72. Consistencia eventual

Las réplicas podrán alcanzar consistencia eventual,
pero la metadata principal deberá indicar claramente:

- cuál copia está activa;
- cuál está pendiente;
- cuál está verificada;
- cuál está degradada.

---

# 73. Consistencia fuerte para identidad

Se exigirá consistencia fuerte para:

- file_id;
- versión;
- hash;
- Tenant;
- estado AVAILABLE;
- ubicación primaria;
- eliminación;
- Legal Hold.

---

# 74. Escrituras multi-nodo

Dos nodos no deberán escribir simultáneamente
sobre la misma versión del mismo file_id.

Sí podrán:

- crear versiones distintas;
- crear réplicas coordinadas;
- leer en paralelo;
- procesar derivados separados.

---

# 75. Cambio de versión durante movimiento

Si se crea una nueva versión mientras una versión anterior se mueve:

- cada versión conserva su propio estado;
- no se bloquea necesariamente la nueva;
- no se confunden hashes;
- no se sobrescribe la anterior.

---

# 76. Cifrado

Los archivos podrán estar cifrados:

- en tránsito;
- en reposo;
- en backups.

Cada ubicación deberá registrar:

- encryption_status;
- key_reference;
- algorithm;
- rotation_status.

---

# 77. Gestión de claves

Las claves no deberán almacenarse junto al archivo
sin protección.

El acceso deberá estar restringido y auditado.

---

# 78. Rotación de claves

La rotación no deberá destruir acceso histórico.

Podrá realizarse mediante:

- reenvoltura de claves;
- re-encriptación;
- versionado;
- proceso controlado.

---

# 79. Acceso temporal

Las descargas usarán URLs temporales.

Estas deberán:

- expirar;
- estar limitadas al objeto;
- no permitir listar;
- no permitir escribir;
- respetar permisos;
- registrar uso cuando corresponda.

---

# 80. Storage Keys

La clave física podrá tener formato:

```text
tenant_id/
file_id/
version/
object_hash
```

No dependerá únicamente del nombre visible.

---

# 81. Nombres humanos

El nombre visible podrá cambiar
sin mover físicamente el archivo.

La relación se mantiene mediante metadata.

---

# 82. Multi-tenant

Toda operación deberá incluir:

- tenant_id;
- file_id;
- version_id;
- operation_id.

No se permitirá:

- mover a otro Tenant;
- replicar cruzando Tenant;
- generar enlaces de otro Tenant;
- mezclar metadata.

---

# 83. Deduplicación global

Si en el futuro se implementa deduplicación física global:

- cada Tenant conservará su propia referencia lógica;
- los permisos seguirán aislados;
- las claves de cifrado deberán respetar aislamiento;
- la eliminación de un Tenant no eliminará objetos usados por otro;
- no se expondrá que otro Tenant posee el mismo archivo.

---

# 84. Auditoría

Cada operación registrará:

- tenant_id;
- file_id;
- version_id;
- operation_id;
- action;
- source;
- destination;
- actor;
- service;
- node;
- start_time;
- end_time;
- hash_before;
- hash_after;
- result;
- error;
- retry_count.

---

# 85. Eventos

Eventos posibles:

```text
storage.write.started
storage.write.completed
storage.write.failed
storage.replication.started
storage.replication.completed
storage.replication.failed
storage.move.started
storage.move.completed
storage.move.failed
storage.integrity.failed
storage.repair.started
storage.repair.completed
storage.node.degraded
storage.node.offline
storage.rebalance.started
storage.rebalance.completed
storage.restore.completed
```

---

# 86. Integración con Event Bus

Los eventos deberán ser persistentes
cuando afecten integridad o disponibilidad.

---

# 87. Integración con Rule Engine

El Rule Engine podrá decidir:

- número de réplicas;
- prioridad;
- retención;
- región;
- archivo crítico;
- permiso de eliminación;
- reacción ante degradación.

---

# 88. Integración con Workflow Engine

El Workflow Engine coordinará:

- replicación;
- rebalanceo;
- reparación;
- restauración;
- archivado;
- eliminación segura.

---

# 89. Integración con Health Model

El Storage deberá reportar:

- capacidad;
- latencia;
- errores;
- réplicas degradadas;
- corrupción;
- locks activos;
- operaciones bloqueadas;
- nodos offline;
- cola de reparación.

---

# 90. Métricas

Se medirá:

- bytes totales;
- bytes útiles;
- factor de replicación;
- archivos disponibles;
- archivos degradados;
- archivos corruptos;
- operaciones pendientes;
- tiempo de escritura;
- tiempo de réplica;
- tasa de fallos;
- capacidad libre;
- locks vencidos;
- reparaciones.

---

# 91. Alertas

Ejemplos:

```text
STORAGE_CAPACITY_HIGH
STORAGE_CAPACITY_CRITICAL
REPLICA_COUNT_BELOW_MINIMUM
HASH_MISMATCH
NODE_OFFLINE
LOCK_STUCK
REBALANCE_FAILED
RESTORE_FAILED
ORPHAN_OBJECT_FOUND
MISSING_OBJECT_FOUND
```

---

# 92. Backpressure

Si Storage está saturado:

- se limita nueva carga;
- se reduce concurrencia;
- se pausa rebalanceo no crítico;
- se priorizan escrituras pendientes;
- se conserva integridad.

---

# 93. Modo seguro

En modo seguro:

- se bloquean movimientos no esenciales;
- se bloquean eliminaciones;
- se permite lectura;
- se permite reparación;
- se conserva auditoría;
- se prioriza estabilidad.

---

# 94. Shadow Mode

Antes de ejecutar un rebalanceo,
el sistema podrá simular:

- archivos afectados;
- bytes movidos;
- tiempo;
- costo;
- riesgo;
- nodos destino.

---

# 95. Recuperación tras caída

Después de reiniciar, el sistema deberá revisar:

- operaciones WRITING;
- MOVING;
- REPLICATING;
- REPAIRING;
- RESTORING;
- locks vencidos;
- destinos incompletos;
- orígenes activos.

---

# 96. Operaciones huérfanas

Una operación sin Worker activo deberá pasar a:

```text
RECOVERY_PENDING
```

Otro Worker podrá retomarla.

---

# 97. Prioridad de recuperación

Orden sugerido:

```text
1. File Object AVAILABLE sin réplica mínima
2. Objetos con hash inconsistente
3. Movimientos incompletos
4. Replicaciones incompletas
5. Rebalanceo
6. Archivado
```

---

# 98. Pruebas obligatorias

Deberán existir pruebas para:

- caída durante escritura;
- caída durante copia;
- hash distinto;
- nodo lleno;
- nodo offline;
- lock vencido;
- dos movimientos simultáneos;
- lectura durante movimiento;
- réplica corrupta;
- restauración;
- objeto huérfano;
- referencia rota;
- Tenant incorrecto;
- rebalanceo con nuevas escrituras;
- eliminación bloqueada por Legal Hold.

---

# 99. Prueba de movimiento

Escenario:

```text
Origen A
↓
Copiar a B
↓
falla al 50 %
```

Resultado esperado:

```text
A sigue activo
B no se activa
no hay pérdida
operación reintentable
```

---

# 100. Prueba de conmutación

Escenario:

```text
B verificado
↓
Primary cambia a B
↓
nodo falla antes de retirar A
```

Resultado esperado:

```text
A y B existen
PostgreSQL identifica cuál es activo
no hay corrupción
```

---

# 101. Prueba de réplica corrupta

Escenario:

```text
Réplica B hash inválido
```

Resultado esperado:

```text
B aislada
A sigue sirviendo
nueva réplica creada
alerta registrada
```

---

# 102. Prueba de concurrencia

Escenario:

```text
Worker 1 mueve DOC-100
Worker 2 intenta mover DOC-100
```

Resultado esperado:

```text
solo uno adquiere lock
el otro espera o retorna operación existente
```

---

# 103. Portabilidad

El protocolo no deberá depender exclusivamente de:

- un proveedor cloud;
- un tipo de disco;
- una VPS;
- un sistema operativo;
- una marca de NAS.

---

# 104. Regla de continuidad

La pérdida total de un nodo
no deberá significar la pérdida del archivo.

---

# 105. Reglas supremas

## Regla Suprema 1

NINGÚN ARCHIVO SERÁ CONSIDERADO SEGURO
HASTA VALIDAR HASH, METADATA Y POLÍTICA DE RÉPLICA.

## Regla Suprema 2

POSTGRESQL ES LA FUENTE DE VERDAD SOBRE IDENTIDAD,
ESTADO Y UBICACIÓN.

## Regla Suprema 3

TODO MOVIMIENTO SERÁ COPY + VERIFY + SWITCH + RETIRE.

## Regla Suprema 4

NUNCA SE BORRARÁ EL ORIGEN
ANTES DE CONFIRMAR EL DESTINO.

## Regla Suprema 5

DOS NODOS NO PODRÁN MODIFICAR SIMULTÁNEAMENTE
LA MISMA VERSIÓN DEL MISMO ARCHIVO.

## Regla Suprema 6

TODA OPERACIÓN CRÍTICA SERÁ IDEMPOTENTE.

## Regla Suprema 7

LOS LOCKS CRÍTICOS SERÁN DISTRIBUIDOS,
TEMPORALES Y RECUPERABLES.

## Regla Suprema 8

UNA RÉPLICA NO SERÁ ACTIVA
HASTA VERIFICAR SU HASH.

## Regla Suprema 9

UN ARCHIVO DEGRADED DEBERÁ REPARARSE.

## Regla Suprema 10

UNA COPIA CORRUPTA NUNCA SERÁ UTILIZADA PARA LECTURA.

## Regla Suprema 11

LOS BACKUPS INMUTABLES NO PODRÁN BORRARSE
DESDE LA API NORMAL.

## Regla Suprema 12

TODO ARCHIVO PERTENECE A UN TENANT.

## Regla Suprema 13

NINGUNA OPERACIÓN DE STORAGE PODRÁ ROMPER
EL AISLAMIENTO MULTI-TENANT.

## Regla Suprema 14

LA ELIMINACIÓN FÍSICA REQUERIRÁ POLÍTICA,
RETENCIÓN Y AUTORIZACIÓN.

## Regla Suprema 15

LA CAÍDA DE UN NODO NO DEBERÁ PERDER
EL ARCHIVO NI SU TRAZABILIDAD.

## Regla Suprema 16

TODO ESTADO CRÍTICO DE STORAGE
DEBERÁ PERSISTIRSE.

## Regla Suprema 17

LOS OBJETOS HUÉRFANOS NO SE BORRARÁN
AUTOMÁTICAMENTE.

## Regla Suprema 18

TODA RESTAURACIÓN DEBERÁ VALIDAR
INTEGRIDAD Y TENANT.

## Regla Suprema 19

EL REBALANCEO NO TENDRÁ PRIORIDAD
SOBRE LA INTEGRIDAD.

## Regla Suprema 20

FACT CENTRAL PODRÁ CAMBIAR DE PROVEEDOR
O TECNOLOGÍA DE STORAGE SIN CAMBIAR
LA IDENTIDAD LÓGICA DE SUS DOCUMENTOS.
