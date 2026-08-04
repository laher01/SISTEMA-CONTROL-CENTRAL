# FACT CENTRAL

# ARCHITECTURE MAP

Versión: 2.0

Estado: Arquitectura Base

Última actualización: Agosto 2026

---

# OBJETIVO

Este documento representa el mapa maestro de la arquitectura de FACT CENTRAL.

Todo módulo, motor, servicio, componente, API o proceso deberá pertenecer a una única sección de este mapa.

Este documento será la referencia principal para comprender la organización completa del sistema.

---

# ARQUITECTURA GENERAL

FACT CENTRAL

├── PRESENTATION LAYER
│
│   ├── Landing Page
│   ├── Login
│   ├── Registro
│   ├── Dashboard
│   ├── Portal SaaS
│   └── Panel Administrativo
│
├── SAAS PLATFORM
│
│   ├── Tenant Management
│   ├── Subscription Management
│   ├── Billing
│   ├── Trial Management
│   ├── Licensing
│   ├── Permissions
│   └── Identity
│
├── DOCUMENT PLATFORM
│
│   ├── Upload
│   ├── OCR
│   ├── Document Classification
│   ├── Document Validation
│   ├── Document Relation
│   ├── Digital Twin
│   ├── Search
│   ├── Export
│   ├── Archive
│   └── Recovery
│
├── PURCHASE PLATFORM
│
│   ├── Clientes (Receptores)
│   ├── Proveedores
│   ├── Productos
│   ├── Pedidos
│   ├── Compras
│   ├── Expedientes
│   └── Pagos
│
├── BUSINESS INTELLIGENCE
│
│   ├── Executive Dashboard
│   ├── KPIs
│   ├── Reportes
│   ├── Alertas
│   ├── Riesgos
│   ├── Patrones
│   └── IA
│
├── INFRASTRUCTURE
│
│   ├── PostgreSQL
│   ├── Redis
│   ├── Cloudflare
│   ├── Storage
│   ├── FastAPI
│   ├── Background Jobs
│   └── Monitoring
│
└── INTEGRATIONS

    ├── SUNAT
    ├── OpenAI
    ├── WhatsApp
    ├── Correo Electrónico
    ├── Pasarela de Pago
    └── APIs Externas

---

# PRINCIPIOS

1. Cada componente pertenece a un único bloque arquitectónico.

2. Ningún módulo podrá existir fuera de este mapa.

3. Toda nueva funcionalidad deberá ubicarse primero aquí antes de documentarse.

4. La arquitectura deberá mantenerse desacoplada.

5. El sistema crecerá mediante módulos independientes.

6. Toda modificación importante deberá reflejarse primero en este documento.