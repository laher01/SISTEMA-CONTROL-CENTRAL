# ENGINE CATALOG

## FACT CENTRAL

Registro oficial de todos los motores que conforman la arquitectura del sistema.

Versión: 1.0

Estado: Arquitectura Base

Última actualización: Agosto 2026

---

# OBJETIVO

Centralizar el inventario oficial de todos los motores del sistema, indicando su responsabilidad, estado de desarrollo, dependencias y documentación asociada.

Ningún motor podrá incorporarse a la arquitectura sin quedar registrado previamente en este catálogo.

---

# CLASIFICACIÓN

Los motores se agrupan en cinco grandes categorías:

- CORE
- SAAS
- DOCUMENTAL
- INTELIGENCIA
- EJECUTIVO

---

# ESTADOS

🟢 Documentado

🟡 Pendiente de documentación

🔵 En desarrollo

⚪ Planificado

🔴 Descontinuado

---

# 1. CORE ENGINES

| Motor | Estado | Documento |
|--------|---------|-----------|
| Rule Engine | 🟢 | 01_RULE_ENGINE.md |
| Workflow Automation Engine | 🟢 | 02_WORKFLOW_AUTOMATION.md |
| Upload State Machine | 🟢 | 03_UPLOAD_STATE_MACHINE.md |
| Storage Consistency Engine | 🟢 | 04_STORAGE_CONSISTENCY_ENGINE.md |
| Event Bus | 🟢 | 05_EVENT_BUS.md |
| Time Engine | 🟢 | 06_TIME_ENGINE.md |
| Notification Engine | 🟢 | 07_NOTIFICATION_ENGINE.md |
| Core Integration | 🟢 | 08_CORE_INTEGRATION.md |
| Idempotency Strategy | 🟢 | 09_IDEMPOTENCY_STRATEGY.md |
| Resilience & Failure Engine | 🟢 | 10_RESILIENCE_AND_FAILURE.md |

---

# 2. SAAS ENGINES

| Motor | Estado | Documento |
|--------|---------|-----------|
| Tenant Lifecycle Engine | 🟢 | 01_TENANT_LIFECYCLE.md |
| Tenant Isolation Engine | 🟢 | 02_TENANT_ISOLATION_MODEL.md |
| Identity & Access Engine | 🟢 | 03_IDENTITY_AND_ACCESS.md |
| Permission Engine | 🟢 | 04_PERMISSION_ENGINE.md |
| Subscription Engine | 🟢 | 05_SUBSCRIPTION_ENGINE.md |
| Billing Engine | 🟢 | 06_BILLING_ENGINE.md |
| SaaS Master Architecture | 🟢 | 07_SAAS_MASTER_ARCHITECTURE.md |
| Plan Engine | ⚪ | Pendiente |
| License Engine | ⚪ | Pendiente |
| Usage Engine | ⚪ | Pendiente |
| Trial Engine | ⚪ | Pendiente |
| Quota Engine | ⚪ | Pendiente |
| Tenant Configuration Engine | ⚪ | Pendiente |

---

# 3. DOCUMENT ENGINES

| Motor | Estado |
|--------|---------|
| Upload Engine | ⚪ |
| OCR Engine | ⚪ |
| Classification Engine | ⚪ |
| Validation Engine | ⚪ |
| Relation Engine | ⚪ |
| Renaming Engine | ⚪ |
| Index Engine | ⚪ |
| Search Engine | ⚪ |
| Export Engine | ⚪ |
| Recovery Engine | ⚪ |
| Digital Twin Engine | ⚪ |
| File Integrity Engine | ⚪ |

---

# 4. BUSINESS INTELLIGENCE ENGINES

| Motor | Estado |
|--------|---------|
| Product Intelligence Engine | ⚪ |
| Supplier Intelligence Engine | ⚪ |
| Client Intelligence Engine | ⚪ |
| Purchase Intelligence Engine | ⚪ |
| Pattern Analysis Engine | ⚪ |
| Risk Analysis Engine | ⚪ |
| Alert Engine | ⚪ |
| Recommendation Engine | ⚪ |

---

# 5. EXECUTIVE ENGINES

| Motor | Estado |
|--------|---------|
| Dashboard Engine | ⚪ |
| KPI Engine | ⚪ |
| Executive Report Engine | ⚪ |
| Decision Support Engine | ⚪ |
| Strategic Analysis Engine | ⚪ |

---

# REGLAS

1. Todo motor debe tener un único propósito.
2. Ningún motor podrá duplicar responsabilidades.
3. Todo motor debe tener un documento técnico propio.
4. Todo motor debe declarar sus entradas y salidas.
5. Todo motor debe indicar sus dependencias.
6. Ningún motor podrá eliminarse sin actualizar este catálogo.