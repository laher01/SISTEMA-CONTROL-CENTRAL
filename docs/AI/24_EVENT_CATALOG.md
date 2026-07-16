# 24_EVENT_CATALOG.md

# FACT CENTRAL

## EVENT CATALOG

### Catálogo Oficial de Eventos de NEXUS

---

# Objetivo

Definir el catálogo oficial de eventos utilizados por FACT CENTRAL.

Todo cambio importante dentro del ERP deberá generar uno o más eventos.

Los eventos constituyen el mecanismo oficial de comunicación entre motores, agentes y servicios.

---

# Filosofía

Los motores no se comunican directamente.

Se comunican mediante eventos.

Un evento representa un hecho que ya ocurrió.

Los eventos son inmutables.

Nunca se modifican.

---

# Estructura Base

Todo evento deberá contener:

event_id

event_type

event_version

event_timestamp

organization_id

correlation_id

request_id

source

target

priority

status

payload

metadata

---

# Estados

CREATED

PUBLISHED

PROCESSING

COMPLETED

FAILED

CANCELLED

RETRY

ARCHIVED

---

# Prioridades

CRITICAL

HIGH

NORMAL

LOW

BACKGROUND

---

# Categorías

Sistema

Seguridad

Documentos

Expedientes

Empresas

Usuarios

Pagos

IA

Misiones

Dashboard

Auditoría

Integraciones

Infraestructura

---

# Eventos de Autenticación

USER_LOGIN

USER_LOGOUT

USER_CREATED

USER_UPDATED

USER_DELETED

PASSWORD_CHANGED

TOKEN_REFRESHED

PERMISSION_GRANTED

PERMISSION_REVOKED

---

# Eventos de Empresas

COMPANY_CREATED

COMPANY_UPDATED

COMPANY_DELETED

COMPANY_VERIFIED

COMPANY_BLOCKED

COMPANY_REACTIVATED

---

# Eventos de Expedientes

EXPEDIENT_CREATED

EXPEDIENT_UPDATED

EXPEDIENT_COMPLETED

EXPEDIENT_ARCHIVED

EXPEDIENT_REOPENED

EXPEDIENT_CANCELLED

---

# Eventos Documentales

DOCUMENT_UPLOADED

DOCUMENT_CLASSIFIED

DOCUMENT_OCR_COMPLETED

DOCUMENT_VALIDATED

DOCUMENT_RELATED

DOCUMENT_DUPLICATED

DOCUMENT_REJECTED

DOCUMENT_DELETED

---

# Eventos Financieros

PAYMENT_REGISTERED

PAYMENT_UPDATED

PAYMENT_CANCELLED

COMMISSION_CALCULATED

BANK_TRANSFER_VALIDATED

DETRACTION_REGISTERED

RETENTION_REGISTERED

---

# Eventos de IA

OCR_STARTED

OCR_COMPLETED

OCR_FAILED

AI_ANALYSIS_STARTED

AI_ANALYSIS_COMPLETED

AI_REASONING_COMPLETED

AI_DECISION_CREATED

AI_LEARNING_COMPLETED

MODEL_UPDATED

PROMPT_UPDATED

---

# Eventos de Misiones

MISSION_CREATED

MISSION_STARTED

MISSION_COMPLETED

MISSION_CANCELLED

MISSION_FAILED

MISSION_REOPENED

TASK_CREATED

TASK_COMPLETED

---

# Eventos Estratégicos

GOAL_CREATED

GOAL_COMPLETED

STRATEGY_CREATED

STRATEGY_UPDATED

PRIORITY_CHANGED

RESOURCE_ASSIGNED

RESOURCE_RELEASED

---

# Eventos del Dashboard

DASHBOARD_UPDATED

KPI_UPDATED

ALERT_CREATED

ALERT_CLOSED

REPORT_GENERATED

---

# Eventos de Auditoría

AUDIT_CREATED

AUDIT_COMPLETED

AUDIT_FAILED

LOG_CREATED

ERROR_REGISTERED

---

# Eventos del Sistema

SYSTEM_STARTED

SYSTEM_STOPPED

SYSTEM_ERROR

SYSTEM_RECOVERED

BACKUP_STARTED

BACKUP_COMPLETED

RESTORE_COMPLETED

---

# Eventos de Integraciones

SUNAT_CONNECTED

SUNAT_ERROR

OPENAI_CONNECTED

OPENAI_ERROR

WHATSAPP_SENT

EMAIL_SENT

API_TIMEOUT

API_RETRY

---

# Flujo de Eventos

Evento

↓

Event Bus

↓

Event Router

↓

Motor

↓

Agente

↓

Respuesta

↓

Nuevo Evento

---

# Reglas

Todo evento deberá:

tener UUID;

ser inmutable;

tener versión;

registrar fecha;

registrar origen;

registrar organización;

registrar correlación.

---

# Versionado

Todo evento tendrá:

event_version

Ejemplo

1.0

1.1

2.0

---

# Idempotencia

El mismo evento nunca deberá procesarse dos veces.

Cada evento será identificado mediante:

event_id

correlation_id

---

# Retención

Los eventos permanecerán disponibles para auditoría según la política de retención configurada.

---

# Auditoría

Todo evento registrará:

quién lo publicó;

quién lo procesó;

qué resultado produjo;

tiempo de ejecución;

errores;

reintentos.

---

# Escalabilidad

Permitirá incorporar nuevos eventos sin modificar el Event Bus.

---

# Regla Suprema

Todo cambio relevante dentro de FACT CENTRAL deberá representarse mediante un evento.

Ningún motor podrá modificar el estado del sistema sin generar el evento correspondiente.

El Event Catalog constituye el lenguaje oficial de comunicación de NEXUS.
