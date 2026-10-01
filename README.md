# FACT CENTRAL

## Plataforma SaaS Inteligente para Gestión Documental Tributaria y Control Integral de Compras Empresariales

FACT CENTRAL es una plataforma SaaS multiempresa (Multi-Tenant) diseñada para administrar, organizar y auditar digitalmente los procesos documentarios de compras de empresas.

No es un sistema de facturación.

No es un ERP tradicional.

Su objetivo es convertir miles de documentos tributarios en expedientes digitales inteligentes completamente relacionados, trazables y listos para procesos de auditoría, control interno y toma de decisiones.

---

# Objetivo

Centralizar toda la documentación de compras de una organización en un único sistema inteligente que permita:

• Control documental.
• Automatización de expedientes.
• Auditoría tributaria preventiva.
• Inteligencia de compras.
• Gestión de proveedores.
• Control de pedidos.
• Seguimiento de pagos.
• Evidencias digitales.
• Reportes ejecutivos.

---

# Problemas que resuelve

Actualmente las empresas almacenan documentos dispersos entre:

- Correos electrónicos
- WhatsApp
- Carpetas compartidas
- PDF
- Imágenes
- Voucher
- Guías
- Contratos

FACT CENTRAL convierte automáticamente toda esa información en expedientes digitales relacionados.

---

# Arquitectura

FACT CENTRAL está construido como una plataforma SaaS Multi-Tenant.

Cada Administrador posee un espacio completamente independiente donde administra:

- Clientes
- Proveedores
- Usuarios
- Gestores
- Documentos
- Expedientes
- Pedidos
- Pagos
- Productos
- Evidencias
- Dashboards

Todo aislado del resto de clientes de la plataforma.

---

# Motores principales

- Motor de Ingesta Documental
- Motor de Clasificación Inteligente
- Motor de Expedientes
- Motor de Evidencias
- Motor de Productos y Servicios
- Motor de Pedidos
- Motor de Distribución
- Motor de Pagos
- Motor de Alertas
- Motor de Auditoría Tributaria
- Motor de Reportes Ejecutivos

---

# Flujo General

Gestor

↓

Usuario

↓

Centro de Ingesta Documental

↓

Clasificación Inteligente

↓

Motor de Reglas

↓

Expedientes Digitales

↓

Dashboards

↓

Reportes

↓

Auditoría

---

# Tecnologías

Backend

Python

FastAPI

PostgreSQL

Redis

Docker

Frontend

React

Cloudflare

Almacenamiento

Object Storage

Sistema distribuido

Replicación

Seguridad

Cloudflare

HTTPS

JWT

RBAC

Auditoría completa

---

# Estado del Proyecto

La arquitectura funcional está documentada. El foco actual es construir y validar el **MVP** con documentos reales:

- [`docs/MVP.md`](docs/MVP.md) — alcance, criterios de éxito y lo que queda fuera.
- [`docs/ESQUEMA_MVP.md`](docs/ESQUEMA_MVP.md) — esquema de datos único del MVP.
- [`docs/futuro/`](docs/futuro/) — visión a largo plazo (NEXUS, agentes, infraestructura avanzada), fuera del alcance actual.

## Ejecución local del MVP

Para probar FACT CENTRAL sin autenticación ni Docker:

- Windows: ejecuta `iniciar-local.cmd`.
- Linux/macOS: ejecuta `./iniciar-local.sh`.

El iniciador crea una base SQLite local, conserva los documentos en
`backend/storage_local` y abre la interfaz en `http://127.0.0.1:5173`.
PostgreSQL continúa siendo la base oficial para despliegues y validación de producción.

La extracción de texto PDF funciona con las dependencias del backend. Para OCR de imágenes
debe instalarse Tesseract; el paquete de idioma español mejora el reconocimiento de documentos
peruanos. Los resultados OCR conservan motor, idioma y confianza y no se aplican como
clasificación definitiva sin confirmación humana.

---

# Filosofía

"No desarrollamos un software.

Construimos una plataforma inteligente capaz de comprender, organizar y controlar la documentación empresarial."
