# FACT CENTRAL

# MASTER DOCUMENTATION INDEX

Versión: 1.0

Estado: Arquitectura Base

Última actualización: Agosto 2026

---

# OBJETIVO

Este documento constituye el índice maestro de toda la documentación del proyecto FACT CENTRAL.

Su finalidad es mantener organizada la arquitectura documental y servir como guía oficial durante el desarrollo del sistema.

Ningún documento nuevo deberá crearse sin verificar previamente este índice.

---

# ESTRUCTURA GENERAL

FACT CENTRAL

│

├── 00 FOUNDATION
│
├── 01 BUSINESS
│
├── 02 PLATFORMS
│
├── 03 MODULES
│
├── 04 ENGINES
│
├── 05 SERVICES
│
├── 06 COMPONENTS
│
├── 07 SECURITY
│
├── 08 AI
│
├── 09 DATABASE
│
├── 10 API
│
├── 11 OPERATIONS
│
└── 12 DEPLOYMENT

---

# 00 FOUNDATION

Estos documentos definen la identidad del proyecto.

- README.md
- MASTER_PLAN.md
- ARCHITECTURE_MAP.md
- ENGINE_CATALOG.md
- SYSTEM_LIFECYCLE.md
- BUSINESS_PROCESS_FLOW.md
- SMART_EXPEDIENT.md
- DOMAIN_MODEL.md

---

# 01 BUSINESS

Modelo de negocio.

- BUSINESS_MODEL.md
- BUSINESS_RULES.md
- BUSINESS_WORKFLOW.md
- ENTITY_RELATION_MAP.md
- PERMISSION_MATRIX.md
- USER_ROLES.md

---

# 02 PLATFORMS

Cada plataforma agrupa módulos relacionados.

## SaaS Platform

- SAAS_PLATFORM.md

## Document Platform

- DOCUMENT_PLATFORM.md

## Purchase Platform

- PURCHASE_PLATFORM.md

## Payment Platform

- PAYMENT_PLATFORM.md

## Executive Platform

- EXECUTIVE_PLATFORM.md

## Intelligence Platform

- INTELLIGENCE_PLATFORM.md

## Communication Platform

- COMMUNICATION_PLATFORM.md

## Security Platform

- SECURITY_PLATFORM.md

---

# 03 MODULES

Cada plataforma está formada por módulos.

Ejemplo:

DOCUMENT PLATFORM

- Upload Module
- OCR Module
- Classification Module
- Validation Module
- Relation Module
- Search Module
- Archive Module
- Export Module

PURCHASE PLATFORM

- Clientes
- Proveedores
- Pedidos
- Productos
- Compras
- Pagos

---

# 04 ENGINES

Motores de procesamiento.

CORE

SAAS

DOCUMENT

BUSINESS

AI

EXECUTIVE

Ver:

ENGINE_CATALOG.md

---

# 05 SERVICES

Servicios compartidos.

- Storage Service
- Notification Service
- Mail Service
- OCR Service
- Backup Service
- Replication Service
- Logging Service
- Authentication Service

---

# 06 COMPONENTS

Componentes tecnológicos.

- PostgreSQL
- Redis
- RabbitMQ
- FastAPI
- Cloudflare
- Docker
- Nginx
- Object Storage

---

# 07 SECURITY

Toda la arquitectura de seguridad.

- SECURITY_ARCHITECTURE.md
- AUTHENTICATION.md
- AUTHORIZATION.md
- JWT.md
- MFA.md
- AUDIT.md
- BACKUP.md
- DISASTER_RECOVERY.md

---

# 08 AI

Toda la inteligencia del sistema.

- MEMORY_SYSTEM.md
- KNOWLEDGE_GRAPH.md
- REASONING_ENGINE.md
- GOAL_ENGINE.md
- STRATEGY_ENGINE.md
- EXECUTIVE_INTELLIGENCE.md

---

# 09 DATABASE

Modelo de datos.

- DATABASE_ARCHITECTURE.md
- DATA_MODEL.md
- DATABASE_SCHEMA.md
- DATABASE_RELATIONS.md

---

# 10 API

APIs.

- API_CONTRACTS.md
- API_DESIGN_GUIDE.md
- API_STYLE_GUIDE.md

---

# 11 OPERATIONS

Operación del sistema.

- SYSTEM_LIFECYCLE.md
- DOCUMENT_LIFECYCLE.md
- EXPEDIENT_LIFECYCLE.md
- DEPLOYMENT_WORKFLOW.md

---

# 12 DEPLOYMENT

Infraestructura.

- DEPLOYMENT_ARCHITECTURE.md
- INFRASTRUCTURE_TOPOLOGY.md
- CAPACITY_PLANNING.md
- COST_MODEL.md
- HEALTH_MODEL.md
- AUTONOMOUS_OPERATIONS_CENTER.md

---

# REGLAS

1. Ningún documento podrá existir fuera de esta estructura.

2. Toda nueva documentación deberá agregarse primero aquí.

3. Toda modificación arquitectónica deberá actualizar este índice.

4. Este documento constituye la guía oficial de la documentación del proyecto.

5. El orden de construcción seguirá esta jerarquía:

FOUNDATION

↓

BUSINESS

↓

PLATFORMS

↓

MODULES

↓

ENGINES

↓

SERVICES

↓

COMPONENTS

↓

DATABASE

↓

API

↓

DEPLOYMENT