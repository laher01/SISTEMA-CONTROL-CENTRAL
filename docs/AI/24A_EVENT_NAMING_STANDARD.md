# 24A_EVENT_NAMING_STANDARD.md

# FACT CENTRAL

## EVENT NAMING STANDARD

### Estándar Oficial para el Nombrado de Eventos

---

# Objetivo

Definir las reglas oficiales para nombrar todos los eventos de FACT CENTRAL.

Este estándar garantiza uniformidad, claridad y compatibilidad entre todos los motores, agentes, APIs e integraciones.

---

# Filosofía

Un evento representa un hecho ocurrido.

Por lo tanto, su nombre debe describir claramente:

- qué ocurrió;
- sobre qué entidad ocurrió;
- cuál fue el resultado.

---

# Principios

Todo evento deberá ser:

- claro;
- único;
- descriptivo;
- consistente;
- escalable;
- versionable.

---

# Estructura Oficial

Todos los eventos utilizarán el formato:

```
ENTIDAD_ACCION
```

Ejemplos

```
DOCUMENT_CREATED

DOCUMENT_UPDATED

EXPEDIENT_COMPLETED

MISSION_STARTED

PAYMENT_APPROVED
```

Nunca utilizar

```
CreateDocument

DocCreated

upload_document

DocumentoCreado
```

---

# Convención

Siempre utilizar:

- MAYÚSCULAS.
- Snake Case.
- Idioma inglés.
- Verbos en participio o estado.

---

# Orden

Siempre

```
ENTIDAD

↓

ACCIÓN
```

Ejemplo

```
DOCUMENT_UPLOADED
```

No

```
UPLOADED_DOCUMENT
```

---

# Entidades Permitidas

USER

ROLE

PERMISSION

COMPANY

DOCUMENT

EXPEDIENT

PRODUCT

PAYMENT

MISSION

TASK

EVENT

RESOURCE

GOAL

STRATEGY

PRIORITY

MODEL

PROMPT

REPORT

ALERT

AUDIT

SYSTEM

API

EMAIL

WHATSAPP

DASHBOARD

OCR

AI

---

# Acciones Permitidas

CREATED

UPDATED

DELETED

UPLOADED

DOWNLOADED

STARTED

COMPLETED

FAILED

CANCELLED

APPROVED

REJECTED

VALIDATED

ARCHIVED

RESTORED

LINKED

UNLINKED

ASSIGNED

RELEASED

PROCESSED

CLASSIFIED

GENERATED

SENT

RECEIVED

OPENED

CLOSED

LOCKED

UNLOCKED

VERIFIED

SCHEDULED

RETRIED

TIMEOUT

EXPIRED

---

# Ejemplos Correctos

```
DOCUMENT_CREATED

DOCUMENT_CLASSIFIED

DOCUMENT_RELATED

EXPEDIENT_COMPLETED

PAYMENT_APPROVED

MISSION_STARTED

TASK_COMPLETED

USER_LOGIN

MODEL_UPDATED

REPORT_GENERATED
```

---

# Eventos Compuestos

Cuando sea necesario agregar contexto adicional se utilizará:

```
ENTIDAD_ACCION_RESULTADO
```

Ejemplos

```
DOCUMENT_VALIDATION_FAILED

MISSION_EXECUTION_COMPLETED

PAYMENT_APPROVAL_REJECTED

API_CONNECTION_TIMEOUT
```

---

# Eventos del Sistema

Siempre comenzarán con

```
SYSTEM_
```

Ejemplos

```
SYSTEM_STARTED

SYSTEM_STOPPED

SYSTEM_RECOVERED

SYSTEM_ERROR
```

---

# Eventos IA

Siempre comenzarán con

```
AI_

OCR_

MODEL_

PROMPT_
```

Ejemplos

```
AI_REASONING_COMPLETED

OCR_COMPLETED

MODEL_SELECTED

PROMPT_EXECUTED
```

---

# Eventos de Integraciones

Siempre comenzarán con el proveedor.

Ejemplo

```
SUNAT_RESPONSE_RECEIVED

OPENAI_REQUEST_SENT

APIPERU_RESPONSE_RECEIVED

WHATSAPP_MESSAGE_SENT
```

---

# Eventos de Seguridad

Prefijo

```
SECURITY_
```

Ejemplos

```
SECURITY_LOGIN_FAILED

SECURITY_PERMISSION_DENIED

SECURITY_TOKEN_EXPIRED
```

---

# Versionado

Todo evento incluirá

```
event_version
```

Ejemplo

```
1.0

1.1

2.0
```

---

# Compatibilidad

Nunca reutilizar un nombre para representar otro significado.

Si cambia el comportamiento del evento:

crear una nueva versión.

---

# Deprecación

Cuando un evento deje de utilizarse deberá marcarse como

```
DEPRECATED
```

Nunca eliminarlo sin migración.

---

# Registro

Todo nuevo evento deberá registrarse previamente en

```
24_EVENT_CATALOG.md
```

No podrán existir eventos fuera del catálogo oficial.

---

# Validación

Antes de crear un evento verificar:

✓ Entidad válida.

✓ Acción válida.

✓ Nombre único.

✓ Documentado.

✓ Versionado.

✓ Compatible.

---

# Auditoría

Toda creación o modificación de eventos registrará:

autor;

fecha;

versión;

motivo;

impacto.

---

# Escalabilidad

Este estándar permitirá incorporar miles de eventos manteniendo una nomenclatura uniforme.

---

# Regla Suprema

Todo evento utilizado por FACT CENTRAL deberá cumplir obligatoriamente este estándar.

El nombre de un evento constituye parte del contrato oficial de comunicación entre los componentes de NEXUS.
