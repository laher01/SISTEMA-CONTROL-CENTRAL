# 03_UPLOAD_STATE_MACHINE.md

# FACT CENTRAL SaaS

## UPLOAD STATE MACHINE

Versión 1.0

---

# 1. Objetivo

Definir la máquina oficial de estados para la carga de archivos
en FACT CENTRAL.

Este documento establece:

- cómo comienza una carga;
- cómo se identifica;
- cómo se recibe por partes;
- cómo se confirma su integridad;
- cómo se almacena;
- cómo se recupera después de una interrupción;
- cómo se evita la duplicidad;
- cómo se rechaza un archivo inválido;
- cómo se reanuda una carga;
- cómo se audita todo el proceso.

La máquina de estados deberá aplicarse a archivos recibidos por:

- carga web;
- aplicación móvil futura;
- correo;
- WhatsApp;
- API;
- integraciones;
- carga masiva;
- procesos internos autorizados.

---

# 2. Principio fundamental

Ningún archivo podrá considerarse recibido únicamente porque
el navegador comenzó a enviarlo.

Un archivo será oficialmente recibido cuando:

- todos sus bytes hayan llegado;
- su tamaño coincida;
- su hash haya sido calculado;
- su integridad haya sido verificada;
- su Tenant haya sido confirmado;
- su origen haya sido registrado;
- su almacenamiento inicial haya sido confirmado.

---

# 3. Separación de conceptos

FACT CENTRAL distinguirá:

## Upload Session

Sesión temporal de carga.

## Ingestion Record

Registro persistente del intento de ingreso.

## File Object

Objeto digital almacenado.

## Logical Document

Documento lógico identificado por el sistema.

## CPE

Entidad fiscal lógica, cuando corresponda.

Una carga puede producir:

- un archivo nuevo;
- un archivo duplicado;
- una nueva representación del mismo CPE;
- un archivo inválido;
- una evidencia complementaria;
- un conflicto fiscal.

---

# 4. Fórmula general

```text
INICIAR CARGA
      ↓
CREAR SESIÓN
      ↓
RECIBIR FRAGMENTOS
      ↓
COMPLETAR TRANSFERENCIA
      ↓
CALCULAR HASH
      ↓
VALIDAR INTEGRIDAD
      ↓
VALIDAR SEGURIDAD
      ↓
ALMACENAR EN CUARENTENA
      ↓
CONFIRMAR RECEPCIÓN
      ↓
ENVIAR A PROCESAMIENTO
```

---

# 5. Identificadores obligatorios

Toda carga deberá generar:

- upload_session_id;
- ingestion_id;
- tenant_id;
- actor_id;
- active_role;
- user_id, cuando corresponda;
- manager_id, cuando corresponda;
- source_channel;
- original_filename;
- declared_size;
- mime_type_declared;
- idempotency_key;
- correlation_id;
- created_at;
- expires_at.

---

# 6. Estados oficiales

## CREATED

La sesión de carga fue creada.

Todavía no se han recibido bytes.

## UPLOADING

La transferencia está en curso.

## PAUSED

La carga fue interrumpida temporalmente,
pero puede reanudarse.

## UPLOAD_COMPLETED

Todos los fragmentos declarados fueron recibidos.

Todavía no se ha validado la integridad.

## INTEGRITY_CHECK

Se está calculando y verificando el hash.

## SECURITY_SCAN

El archivo está siendo revisado por políticas de seguridad.

## QUARANTINED

El archivo fue almacenado en cuarentena.

## RECEIVED_VERIFIED

La recepción fue confirmada oficialmente.

## DUPLICATE_FILE

El archivo físico ya existe por hash.

## DUPLICATE_LOGICAL_DOCUMENT

El archivo representa un documento lógico ya registrado.

## CONFLICT_DETECTED

Existe conflicto entre identidad y contenido.

## REJECTED

El archivo fue rechazado.

## EXPIRED

La sesión venció sin completarse.

## CANCELLED

La carga fue cancelada explícitamente.

## RECOVERY_PENDING

La carga requiere recuperación tras una falla.

## RECOVERED

La carga fue reconstruida o reanudada correctamente.

## PROCESSING_QUEUED

El archivo fue enviado a la cola de procesamiento.

---

# 7. Diagrama principal de estados

```text
CREATED
   ↓
UPLOADING
   ├──→ PAUSED
   │      ↓
   │   UPLOADING
   │
   ├──→ CANCELLED
   ├──→ EXPIRED
   └──→ UPLOAD_COMPLETED
             ↓
       INTEGRITY_CHECK
             ├──→ REJECTED
             ├──→ DUPLICATE_FILE
             └──→ SECURITY_SCAN
                         ├──→ REJECTED
                         └──→ QUARANTINED
                                      ↓
                               RECEIVED_VERIFIED
                                      ↓
                               PROCESSING_QUEUED
```

---

# 8. Creación de sesión

Antes de recibir el archivo, FACT CENTRAL deberá validar:

- identidad;
- Tenant;
- membresía;
- rol activo;
- permiso document.upload;
- estado del Tenant;
- estado de la suscripción;
- cuota disponible;
- tamaño máximo permitido;
- tipo de archivo permitido;
- canal autorizado.

Si alguna validación falla:

```text
NO SE CREA LA SESIÓN
```

---

# 9. Respuesta inicial

Cuando la sesión sea creada, FACT CENTRAL devolverá:

```text
upload_session_id
ingestion_id
chunk_size
expires_at
upload_url temporal
```

La sesión deberá quedar persistida antes de devolver la respuesta.

---

# 10. Carga fragmentada

Los archivos grandes deberán poder cargarse por fragmentos.

Cada fragmento tendrá:

- upload_session_id;
- chunk_number;
- offset;
- size;
- checksum;
- received_at;
- status.

Esto permitirá reanudar la carga sin empezar desde cero.

---

# 11. Validación de fragmentos

Cada fragmento deberá validarse por:

- número esperado;
- posición;
- tamaño;
- checksum;
- duplicidad;
- orden permitido;
- pertenencia al Tenant.

Un fragmento repetido con el mismo checksum podrá ignorarse
de manera idempotente.

Un fragmento repetido con contenido diferente deberá generar:

```text
CHUNK_CONFLICT
```

---

# 12. Estado UPLOADING

Mientras exista transferencia activa:

```text
state = UPLOADING
```

El sistema deberá registrar:

- bytes recibidos;
- porcentaje;
- último fragmento;
- última actividad;
- velocidad;
- errores;
- intentos.

---

# 13. Pausa

La carga podrá pasar a PAUSED cuando:

- se corte la red;
- se cierre el navegador;
- se pierda temporalmente el nodo;
- el cliente deje de enviar fragmentos;
- exista una interrupción controlada.

PAUSED no significa pérdida.

---

# 14. Reanudación

Para reanudar:

1. el cliente presenta upload_session_id;
2. el Backend valida Tenant y actor;
3. consulta los fragmentos recibidos;
4. informa cuáles faltan;
5. continúa desde el último fragmento válido.

La reanudación no deberá crear una nueva sesión
si la anterior sigue vigente.

---

# 15. Expiración

Una sesión expirará cuando:

- supere el tiempo máximo;
- no tenga actividad;
- no se complete;
- no sea reanudada.

Al expirar:

- se conserva el registro;
- se eliminan temporales según política;
- se registra la causa;
- no se crea un documento lógico;
- se puede iniciar una nueva sesión.

---

# 16. Carga completada

Cuando todos los fragmentos hayan sido recibidos:

```text
state = UPLOAD_COMPLETED
```

En este estado todavía no deberá afirmarse:

```text
archivo recibido correctamente
```

Falta validar integridad y seguridad.

---

# 17. Integridad

El estado INTEGRITY_CHECK deberá comprobar:

- tamaño real;
- tamaño declarado;
- hash completo;
- continuidad de fragmentos;
- ausencia de bytes faltantes;
- formato básico;
- consistencia del ensamblaje.

---

# 18. Hash oficial

Se calculará un hash criptográfico del archivo completo.

Ejemplo conceptual:

```text
SHA-256
```

El hash será utilizado para:

- integridad;
- duplicados físicos;
- versionado;
- auditoría;
- verificación de réplicas.

---

# 19. Diferencia entre hashes

El sistema podrá manejar:

## Chunk Hash

Hash de cada fragmento.

## File Hash

Hash del archivo completo.

## Content Fingerprint

Huella normalizada opcional para detectar
archivos visualmente equivalentes.

El hash físico no sustituye la identidad fiscal del CPE.

---

# 20. Falla durante INTEGRITY_CHECK

Si el nodo falla durante el cálculo:

```text
state = RECOVERY_PENDING
```

El sistema deberá:

- conservar upload_session_id;
- conservar fragmentos;
- conservar ensamblado temporal, si existe;
- no crear documento lógico;
- reanudar el cálculo en otro Worker;
- usar la misma ingestion_id.

No se generará una segunda carga.

---

# 21. Duplicado físico

Si el hash completo ya existe dentro del Tenant:

```text
state = DUPLICATE_FILE
```

El sistema deberá determinar:

- si es una recepción repetida;
- si se asocia al mismo documento lógico;
- si proviene de otro canal;
- si debe registrarse como evidencia de trazabilidad.

No se duplicará almacenamiento innecesario,
salvo política de réplica.

---

# 22. Duplicado físico entre Tenants

Aunque el hash coincida:

```text
TENANT A
≠
TENANT B
```

No se compartirá acceso ni metadata.

La deduplicación física global, si existiera,
será transparente y no romperá el aislamiento lógico.

---

# 23. Escaneo de seguridad

En SECURITY_SCAN se verificará:

- malware;
- macros;
- archivos ejecutables;
- contenido incrustado;
- extensión real;
- MIME real;
- estructura dañada;
- archivos protegidos;
- compresión sospechosa;
- tamaño expandido;
- riesgos conocidos.

---

# 24. Extensión y MIME

El sistema no confiará únicamente en el nombre.

Ejemplo:

```text
factura.pdf
```

podría no ser realmente un PDF.

Se deberá comprobar:

- extensión;
- MIME declarado;
- MIME detectado;
- firma binaria;
- estructura interna.

---

# 25. Archivos permitidos

Inicialmente podrán admitirse:

- PDF;
- JPG;
- JPEG;
- PNG;
- WEBP;
- TIFF;
- XML;
- TXT;
- CSV;
- XLSX;
- ZIP controlado;
- otros autorizados.

La lista será configurable por Plan, módulo y rol.

---

# 26. Archivos comprimidos

Un ZIP podrá aceptarse bajo reglas especiales.

Deberá controlarse:

- cantidad de archivos;
- tamaño comprimido;
- tamaño expandido;
- profundidad;
- tipos internos;
- nombres;
- malware;
- zip bomb.

---

# 27. Archivo malicioso

Si el archivo es peligroso:

```text
state = REJECTED
reason = MALWARE_DETECTED
```

El archivo podrá conservarse en cuarentena técnica
según política de seguridad,
sin quedar disponible al Usuario.

---

# 28. Cuarentena

QUARANTINED significa:

- el archivo existe;
- está aislado;
- no está disponible públicamente;
- no ha sido incorporado al expediente;
- no ha generado impacto económico;
- espera confirmación final.

---

# 29. Confirmación oficial

Solo después de:

- integridad válida;
- seguridad válida;
- almacenamiento confirmado;
- Tenant confirmado;

se cambia a:

```text
RECEIVED_VERIFIED
```

Este es el punto oficial de recepción.

---

# 30. Confirmación al cliente

FACT CENTRAL podrá informar:

```text
Archivo recibido correctamente.

ingestion_id:
ING-123456

Estado:
RECEIVED_VERIFIED
```

Desde este momento el procesamiento puede continuar
aunque el usuario cierre la sesión.

---

# 31. Procesamiento posterior

Después de RECEIVED_VERIFIED:

```text
PROCESSING_QUEUED
```

Se podrá iniciar:

- OCR;
- clasificación;
- separación de PDF;
- identificación de CPE;
- normalización;
- detección de Cliente;
- detección de Proveedor;
- creación de Expediente.

---

# 32. Separación entre recepción y procesamiento

La recepción no dependerá de:

- OCR;
- IA;
- clasificación;
- creación de Expediente;
- consultas externas;
- procesamiento tributario.

Esto evita que una falla posterior destruya la carga.

---

# 33. Idempotency key

Cada intento deberá utilizar una clave de idempotencia.

Podrá construirse con:

- tenant_id;
- actor_id;
- source_channel;
- client_generated_id;
- original filename;
- declared size;
- timestamp controlado.

No deberá depender únicamente del nombre.

---

# 34. Persistencia de idempotencia

Las claves de idempotencia deberán almacenarse
en un sistema persistente.

No deberán depender solo de:

- memoria;
- sesión del navegador;
- Redis sin persistencia;
- nodo específico.

---

# 35. Reintento después de perder la respuesta

Escenario:

```text
Archivo recibido
↓
Backend confirma internamente
↓
respuesta al navegador se pierde
↓
Usuario reintenta
```

El sistema deberá reconocer la misma idempotency_key
y devolver el resultado anterior.

No creará una nueva recepción económica.

---

# 36. Carga simultánea del mismo archivo

Si dos personas cargan el mismo archivo al mismo tiempo:

```text
GESTOR A
+
GESTOR B
```

el sistema podrá recibir ambos intentos,
pero deberá consolidar el resultado físico por hash.

La trazabilidad conservará:

- quién lo envió;
- cuándo;
- por qué canal;
- a qué Usuario pertenece;
- qué recepción fue primera.

---

# 37. Unicidad fiscal

La detección de duplicado fiscal se realizará después
de identificar el CPE.

Clave fiscal:

```text
RUC EMISOR
+
TIPO DE CPE
+
SERIE
+
CORRELATIVO
```

---

# 38. Duplicado lógico

Si un archivo nuevo representa un CPE ya existente:

```text
state = DUPLICATE_LOGICAL_DOCUMENT
```

El archivo se asociará al CPE existente.

No se generará:

- nueva producción;
- nueva comisión;
- nuevo pedido ejecutado;
- nuevo impacto contable.

---

# 39. Múltiples representaciones

Un mismo CPE podrá tener:

- PDF;
- XML;
- imagen;
- captura;
- correo;
- versión descargada;
- copia escaneada.

Todas podrán relacionarse con:

```text
1 CPE lógico
```

---

# 40. Conflicto de identidad fiscal

Si dos archivos presentan la misma identidad fiscal
pero datos distintos:

```text
state = CONFLICT_DETECTED
```

Ejemplos:

- monto diferente;
- fecha diferente;
- receptor diferente;
- moneda diferente;
- contenido incompatible.

El sistema deberá:

- detener impacto económico;
- conservar ambos archivos;
- crear alerta;
- solicitar revisión;
- impedir cierre automático.

---

# 41. Rechazo

Un archivo podrá ser rechazado por:

- tamaño excedido;
- tipo no permitido;
- corrupción;
- malware;
- sesión inválida;
- Tenant inválido;
- cuota agotada;
- suscripción bloqueada;
- hash inconsistente;
- fragmentos incompletos;
- formato ilegible;
- cifrado no autorizado.

---

# 42. Códigos de rechazo

Ejemplos:

```text
REJECT_FILE_TOO_LARGE
REJECT_TYPE_NOT_ALLOWED
REJECT_MALWARE
REJECT_CORRUPTED
REJECT_TENANT_MISMATCH
REJECT_QUOTA_EXCEEDED
REJECT_SESSION_EXPIRED
REJECT_HASH_MISMATCH
REJECT_INCOMPLETE_UPLOAD
REJECT_SECURITY_POLICY
```

---

# 43. Cancelación

El usuario podrá cancelar mientras la carga no esté
en RECEIVED_VERIFIED.

Después de la recepción oficial,
no se cancela la existencia del archivo.

Podrá solicitarse eliminación lógica
según permisos y políticas.

---

# 44. Recuperación después de caída del nodo

Si falla el nodo durante:

## CREATED

La sesión puede recrearse si no persistió.

## UPLOADING

Se reanuda desde fragmentos persistidos.

## UPLOAD_COMPLETED

Se retoma INTEGRITY_CHECK.

## INTEGRITY_CHECK

Se recalcula hash.

## SECURITY_SCAN

Se reejecuta el análisis.

## QUARANTINED

Se verifica existencia y continúa.

## RECEIVED_VERIFIED

No se repite la recepción.

## PROCESSING_QUEUED

El Workflow Engine reanuda procesamiento.

---

# 45. Recuperación determinística

La recuperación deberá determinar el siguiente paso
a partir del último estado persistido.

No deberá depender de memoria del nodo anterior.

---

# 46. Reconciliación al reiniciar

Al iniciar, un Worker podrá buscar:

- sesiones UPLOADING sin actividad;
- UPLOAD_COMPLETED sin hash;
- INTEGRITY_CHECK incompleto;
- SECURITY_SCAN pendiente;
- QUARANTINED sin confirmación;
- RECOVERY_PENDING.

Cada una será retomada según política.

---

# 47. Atomicidad

El paso a RECEIVED_VERIFIED deberá ser atómico.

Deberá confirmarse conjuntamente:

- archivo almacenado;
- hash registrado;
- ingestion record actualizado;
- ubicación registrada;
- estado persistido.

Si falla una parte:

```text
NO SE CONFIRMA RECEPCIÓN
```

---

# 48. Movimiento entre storage

El archivo no deberá moverse durante la recepción oficial
sin un protocolo de consistencia.

El movimiento posterior será responsabilidad de:

```text
STORAGE CONSISTENCY PROTOCOL
```

---

# 49. Nombre original

Siempre se conservará:

```text
original_filename
```

Aunque el sistema genere:

```text
normalized_filename
```

---

# 50. Nombre normalizado

Después de identificar el documento,
FACT CENTRAL podrá generar:

```text
RUC_CLIENTE
+
NOMBRE_CORTO
+
TIPO
+
SERIE_CORRELATIVO
+
FECHA
```

El nombre normalizado no determina la identidad del archivo.

---

# 51. Archivos de múltiples páginas

Un PDF podrá contener:

- una Factura;
- varias Facturas;
- Facturas y Guías;
- anexos;
- documentos mezclados.

La recepción corresponde al archivo completo.

La separación será un Workflow posterior.

---

# 52. Separación de PDF

Después de RECEIVED_VERIFIED:

```text
FILE OBJECT
↓
SEPARATION WORKFLOW
↓
DERIVED FILES
```

Los archivos derivados conservarán:

- parent_file_id;
- page_range;
- hash;
- Tenant;
- origen;
- trazabilidad.

---

# 53. Derivados

Los derivados no deberán borrar el archivo original.

Ejemplos:

- página extraída;
- miniatura;
- OCR text;
- PDF separado;
- imagen normalizada;
- versión comprimida.

---

# 54. Estado visible al usuario

La interfaz podrá mostrar:

```text
Preparando
Subiendo
Pausado
Verificando
Analizando seguridad
Recibido
En procesamiento
Procesado
Duplicado
Observado
Rechazado
```

Los nombres visuales podrán diferir
de los estados técnicos internos.

---

# 55. Progreso

La interfaz podrá mostrar:

```text
35 % subido
100 % transferido
Verificando integridad
Archivo recibido
Procesamiento en cola
```

No deberá mostrar “procesado”
cuando solo terminó la transferencia.

---

# 56. Cargas masivas

Una carga masiva tendrá:

- batch_id;
- cantidad de archivos;
- sesiones independientes;
- resumen;
- errores;
- progreso;
- estado global.

Cada archivo conservará su propia máquina de estados.

---

# 57. Estado del lote

Estados posibles:

```text
BATCH_CREATED
BATCH_UPLOADING
BATCH_PARTIAL
BATCH_COMPLETED
BATCH_WITH_ERRORS
BATCH_CANCELLED
```

Un archivo fallido no deberá cancelar automáticamente todo el lote.

---

# 58. Cuotas

La cuota podrá contabilizarse en distintos momentos:

## Transferencia

Bytes recibidos temporalmente.

## Storage

Archivo confirmado.

## Procesamiento

Documento enviado a OCR o IA.

La política deberá evitar cobrar doble por reintentos idempotentes.

---

# 59. Rate limiting

Se controlará:

- sesiones creadas;
- archivos por hora;
- bytes por periodo;
- fragmentos por segundo;
- intentos fallidos;
- concurrencia por Tenant;
- concurrencia por Usuario.

---

# 60. Cloudflare y DDoS

Cloudflare podrá limitar tráfico,
pero una conexión interrumpida no deberá corromper la carga.

El protocolo fragmentado y reanudable permitirá continuar.

---

# 61. Backpressure

Si el procesamiento está saturado:

```text
RECEIVED_VERIFIED
↓
PROCESSING_QUEUED
```

El archivo permanece seguro.

La saturación de Workers no deberá rechazar
un archivo ya recibido correctamente.

---

# 62. Prioridades

Las cargas podrán clasificarse por:

- Plan;
- criticidad;
- tamaño;
- canal;
- Tenant;
- tipo de documento;
- urgencia.

La prioridad de procesamiento no alterará
la integridad de recepción.

---

# 63. Auditoría

Cada transición deberá registrar:

- tenant_id;
- upload_session_id;
- ingestion_id;
- estado anterior;
- estado nuevo;
- actor;
- rol;
- canal;
- fecha;
- nodo;
- IP;
- bytes;
- hash;
- resultado;
- error;
- motivo.

---

# 64. Métricas

Se medirá:

- sesiones creadas;
- cargas completadas;
- cargas pausadas;
- cargas recuperadas;
- rechazos;
- duplicados;
- conflictos;
- velocidad;
- tiempo de integridad;
- tiempo de escaneo;
- bytes por Tenant;
- errores por canal.

---

# 65. Observabilidad

El Administrador podrá ver:

```text
CARGAS ACTIVAS
PAUSADAS
RECUPERANDO
RECIBIDAS
RECHAZADAS
DUPLICADAS
OBSERVADAS
```

El Gestor o Usuario verá únicamente sus cargas.

---

# 66. Seguridad multi-tenant

Toda operación deberá validar:

```text
session.tenant_id
=
resource.tenant_id
```

No se aceptará tenant_id enviado libremente
como autoridad suficiente.

---

# 67. URLs temporales

Cuando se utilicen URLs prefirmadas:

- tendrán expiración;
- estarán limitadas a un objeto;
- estarán ligadas a Tenant;
- no permitirán listar storage;
- no permitirán sobrescribir otro objeto;
- no serán reutilizables fuera de política.

---

# 68. Permisos

Permisos posibles:

```text
document.upload
document.upload.resume
document.upload.cancel
document.upload.view_status
document.upload.batch
document.upload.retry
document.quarantine.review
```

---

# 69. Identidades técnicas

Los servicios de upload usarán identidades técnicas limitadas.

No tendrán:

- acceso global a todos los Tenants;
- permiso de borrar backups;
- permiso administrativo;
- acceso irrestricto a PostgreSQL.

---

# 70. Privacidad

Los nombres, documentos y metadatos deberán protegerse.

Los logs no deberán exponer innecesariamente:

- contenido completo;
- cuentas bancarias;
- documentos personales;
- datos tributarios sensibles.

---

# 71. Integración con Workflow Engine

Después de RECEIVED_VERIFIED:

```text
workflow.start:
DOCUMENT_PROCESSING
```

El Upload State Machine termina su responsabilidad principal.

---

# 72. Integración con Event Bus

Eventos posibles:

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

# 73. Integración con Notification Engine

Podrán notificarse:

- carga completada;
- carga pausada;
- carga rechazada;
- archivo malicioso;
- duplicado;
- conflicto;
- recuperación exitosa.

---

# 74. Integración con Rule Engine

El Rule Engine podrá evaluar:

- tipo permitido;
- tamaño máximo;
- cuota;
- prioridad;
- necesidad de revisión;
- acción ante duplicado;
- severidad ante conflicto.

---

# 75. Integración con Storage Consistency Protocol

Una vez recibido, el archivo podrá:

- replicarse;
- moverse;
- archivarse;
- versionarse;
- restaurarse.

Estas operaciones serán gobernadas por el protocolo de consistencia.

---

# 76. Pruebas obligatorias

Deberán existir pruebas para:

- corte de red al 10 %;
- corte al 99 %;
- fragmento duplicado;
- fragmento corrupto;
- respuesta perdida;
- nodo caído;
- carga simultánea;
- archivo duplicado;
- Tenant incorrecto;
- malware;
- archivo muy grande;
- sesión expirada;
- lote parcial;
- recuperación.

---

# 77. Prueba de respuesta perdida

Escenario:

```text
Backend confirma RECEIVED_VERIFIED
↓
respuesta no llega al cliente
↓
cliente reintenta
```

Resultado esperado:

```text
mismo ingestion_id
mismo resultado
sin duplicado
```

---

# 78. Prueba de nodo caído

Escenario:

```text
INTEGRITY_CHECK
↓
nodo falla
↓
otro nodo retoma
```

Resultado esperado:

```text
mismo upload_session_id
mismo ingestion_id
hash recalculado
sin pérdida
```

---

# 79. Prueba de concurrencia

Escenario:

```text
dos gestores cargan el mismo PDF
al mismo tiempo
```

Resultado esperado:

- dos registros de recepción;
- un solo archivo físico lógico por hash;
- un solo CPE lógico;
- una sola contabilización;
- trazabilidad de ambos envíos.

---

# 80. Reglas supremas

## Regla Suprema 1

UN ARCHIVO NO SE CONSIDERA RECIBIDO
HASTA VALIDAR INTEGRIDAD, SEGURIDAD Y ALMACENAMIENTO.

## Regla Suprema 2

LA TRANSFERENCIA Y EL PROCESAMIENTO SON ETAPAS DISTINTAS.

## Regla Suprema 3

LA PÉRDIDA DE UNA RESPUESTA NO PODRÁ GENERAR DUPLICADOS.

## Regla Suprema 4

LAS CARGAS INTERRUMPIDAS PODRÁN REANUDARSE.

## Regla Suprema 5

TODO ESTADO CRÍTICO DEBERÁ PERSISTIRSE.

## Regla Suprema 6

NINGÚN ARCHIVO MALICIOSO SERÁ INCORPORADO AL ERP.

## Regla Suprema 7

UN HASH IGUAL IDENTIFICA DUPLICADO FÍSICO,
NO NECESARIAMENTE IDENTIDAD FISCAL.

## Regla Suprema 8

UN CPE LÓGICO SOLO GENERARÁ UN IMPACTO ECONÓMICO.

## Regla Suprema 9

LOS CONFLICTOS FISCALES NO SE RESOLVERÁN SILENCIOSAMENTE.

## Regla Suprema 10

TODO ARCHIVO PERTENECE A UN TENANT DESDE EL INICIO.

## Regla Suprema 11

LA CAÍDA DE UN NODO NO DEBERÁ PERDER LA CARGA.

## Regla Suprema 12

LOS ARCHIVOS ORIGINALES NO SERÁN BORRADOS
POR CREAR DERIVADOS.

## Regla Suprema 13

LOS REINTENTOS SERÁN IDEMPOTENTES.

## Regla Suprema 14

LA CONFIRMACIÓN RECEIVED_VERIFIED SERÁ ATÓMICA.

## Regla Suprema 15

TODAS LAS TRANSICIONES SERÁN AUDITABLES.
