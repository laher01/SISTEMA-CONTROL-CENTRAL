# 24_EVENT_CATALOG.md

# FACT CENTRAL

## EVENT CATALOG

### Catálogo Oficial de Eventos de NEXUS

Versión 1.0

---

# Objetivo

El Event Catalog define todos los eventos oficiales que pueden producirse dentro del ecosistema FACT CENTRAL.

Los eventos representan hechos ocurridos.

Los motores, agentes, APIs e integraciones no se comunican directamente.

Toda comunicación ocurre mediante eventos.

Este documento constituye el lenguaje universal de NEXUS.

---

# Filosofía

NEXUS está basado en Event Driven Architecture (EDA).

Cada acción importante produce un evento.

Cada evento puede ser consumido por uno o varios motores.

Los eventos son:

• Inmutables.

• Auditables.

• Versionados.

• Desacoplados.

• Trazables.

---

# Flujo General

```
Usuario

↓

API

↓

Motor

↓

Evento

↓

Event Bus

↓

Event Router

↓

Motores

↓

Agentes

↓

Respuesta

↓

Nuevo Evento
```

---

# Estructura Oficial

Todo evento deberá contener como mínimo:

```json
{
  "event_id": "uuid",
  "event_name": "DOCUMENT_UPLOADED",
  "event_version": "1.0",
  "organization_id": "uuid",
  "correlation_id": "uuid",
  "request_id": "uuid",
  "timestamp": "2026-07-15T20:30:00Z",
  "source": "Document Engine",
  "target": "Event Bus",
  "priority": "NORMAL",
  "status": "CREATED",
  "payload": {},
  "metadata": {}
}
```

---

# Estados

CREATED

VALIDATED

PUBLISHED

ROUTED

PROCESSING

PROCESSED

FAILED

RETRY

CANCELLED

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

AUTH

USERS

COMPANIES

DOCUMENTS

EXPEDIENTS

PRODUCTS

PAYMENTS

MISSIONS

AI

LEARNING

AUDIT

DASHBOARD

SYSTEM

SECURITY

NOTIFICATIONS

INTEGRATIONS

INFRASTRUCTURE

---

# Eventos de Autenticación

USER_LOGIN

USER_LOGOUT

USER_CREATED

USER_UPDATED

USER_DELETED

PASSWORD_CHANGED

SESSION_STARTED

SESSION_EXPIRED

TOKEN_CREATED

TOKEN_REFRESHED

TOKEN_REVOKED

ROLE_ASSIGNED

ROLE_REMOVED

PERMISSION_GRANTED

PERMISSION_REVOKED

---

# Eventos de Empresas

COMPANY_CREATED

COMPANY_UPDATED

COMPANY_VERIFIED

COMPANY_BLOCKED

COMPANY_UNBLOCKED

COMPANY_ARCHIVED

COMPANY_RESTORED

COMPANY_RELATION_CREATED

COMPANY_RELATION_UPDATED

---

# Eventos Documentales

DOCUMENT_RECEIVED

DOCUMENT_UPLOADED

DOCUMENT_STORED

DOCUMENT_HASH_GENERATED

DOCUMENT_OCR_STARTED

DOCUMENT_OCR_COMPLETED

DOCUMENT_CLASSIFIED

DOCUMENT_VALIDATED

DOCUMENT_RELATED

DOCUMENT_INDEXED

DOCUMENT_DUPLICATE_DETECTED

DOCUMENT_VERSION_CREATED

DOCUMENT_ARCHIVED

DOCUMENT_RESTORED

DOCUMENT_DELETED

---

# Eventos de Expedientes

EXPEDIENT_CREATED

EXPEDIENT_UPDATED

EXPEDIENT_DOCUMENT_ADDED

EXPEDIENT_DOCUMENT_REMOVED

EXPEDIENT_STATUS_CHANGED

EXPEDIENT_COMPLETED

EXPEDIENT_REOPENED

EXPEDIENT_ARCHIVED

EXPEDIENT_DELETED

EXPEDIENT_RISK_UPDATED

---

# Eventos de Productos

PRODUCT_CREATED

PRODUCT_UPDATED

PRODUCT_DELETED

PRODUCT_LINKED

PRODUCT_UNLINKED

---

# Eventos Financieros

PAYMENT_REGISTERED

PAYMENT_UPDATED

PAYMENT_APPROVED

PAYMENT_REJECTED

PAYMENT_CANCELLED

BANK_TRANSFER_VALIDATED

BANK_TRANSFER_REJECTED

COMMISSION_CALCULATED

DETRACTION_REGISTERED

RETENTION_REGISTERED

---

# Eventos de IA

OCR_STARTED

OCR_COMPLETED

OCR_FAILED

CONTEXT_CREATED

REASONING_STARTED

REASONING_COMPLETED

DECISION_CREATED

ACTION_PLAN_CREATED

EXECUTION_STARTED

EXECUTION_COMPLETED

QUALITY_APPROVED

QUALITY_REJECTED

LEARNING_STARTED

LEARNING_COMPLETED

MODEL_SELECTED

MODEL_UPDATED

PROMPT_EXECUTED

---

# Eventos Estratégicos

GOAL_CREATED

GOAL_UPDATED

GOAL_COMPLETED

GOAL_CANCELLED

STRATEGY_CREATED

STRATEGY_APPROVED

STRATEGY_UPDATED

STRATEGY_CANCELLED

PRIORITY_ASSIGNED

PRIORITY_UPDATED

RESOURCE_RESERVED

RESOURCE_ASSIGNED

RESOURCE_RELEASED

RESOURCE_OVERLOADED

---

# Eventos de Misiones

MISSION_CREATED

MISSION_STARTED

MISSION_UPDATED

MISSION_COMPLETED

MISSION_FAILED

MISSION_CANCELLED

TASK_CREATED

TASK_STARTED

TASK_COMPLETED

TASK_FAILED

---

# Eventos del Dashboard

DASHBOARD_UPDATED

KPI_UPDATED

REPORT_GENERATED

ALERT_CREATED

ALERT_UPDATED

ALERT_RESOLVED

---

# Eventos de Auditoría

AUDIT_CREATED

AUDIT_UPDATED

AUDIT_COMPLETED

LOG_REGISTERED

ERROR_REGISTERED

SECURITY_INCIDENT_DETECTED

---

# Eventos del Sistema

SYSTEM_STARTED

SYSTEM_STOPPED

SYSTEM_RESTARTED

SYSTEM_BACKUP_STARTED

SYSTEM_BACKUP_COMPLETED

SYSTEM_RESTORE_COMPLETED

SYSTEM_CONFIGURATION_UPDATED

SYSTEM_ERROR

SYSTEM_RECOVERED

---

# Eventos de Integraciones

SUNAT_REQUEST_SENT

SUNAT_RESPONSE_RECEIVED

APIPERU_REQUEST_SENT

APIPERU_RESPONSE_RECEIVED

OPENAI_REQUEST_SENT

OPENAI_RESPONSE_RECEIVED

WHATSAPP_MESSAGE_SENT

EMAIL_SENT

API_TIMEOUT

API_RETRY

API_FAILURE

---

# Eventos de Infraestructura

SERVER_STARTED

SERVER_STOPPED

SERVER_OVERLOADED

DATABASE_CONNECTED

DATABASE_DISCONNECTED

CACHE_UPDATED

QUEUE_CREATED

QUEUE_OVERFLOW

STORAGE_FULL

---

# Ciclo de Vida del Evento

```
Creación

↓

Validación

↓

Publicación

↓

Enrutamiento

↓

Procesamiento

↓

Confirmación

↓

Auditoría

↓

Archivado
```

---

# Idempotencia

Todo evento deberá ser procesado una sola vez.

La unicidad estará determinada por:

- event_id
- correlation_id
- request_id

---

# Dead Letter Queue

Los eventos que no puedan procesarse después del número máximo de reintentos serán enviados automáticamente a la Dead Letter Queue para su análisis y posible reprocesamiento.

---

# Monitoreo

El sistema medirá:

- eventos publicados;
- eventos procesados;
- tiempo promedio;
- latencia;
- errores;
- reintentos;
- throughput;
- consumo por motor;
- consumo por agente.

---

# Auditoría

Cada evento registrará:

- usuario;
- organización;
- motor origen;
- agente origen;
- fecha;
- duración;
- resultado;
- errores;
- reintentos.

---

# Integración

El Event Catalog será utilizado por:

- Event Bus;
- Event Router;
- Scheduler;
- Todos los Motores;
- Todos los Agentes;
- Dashboard;
- Auditoría;
- Learning System;
- Executive Intelligence Engine.

---

# Escalabilidad

Nuevos eventos podrán añadirse sin modificar la arquitectura principal.

Todo nuevo evento deberá:

- cumplir el estándar de nombres;
- documentarse;
- versionarse;
- registrarse en este catálogo.

---

# Regla Suprema

Todo cambio relevante dentro de FACT CENTRAL deberá representarse mediante un evento oficial registrado en este catálogo.

El Event Catalog constituye el lenguaje universal de comunicación de NEXUS y es el contrato oficial entre motores, agentes, servicios e integraciones.
