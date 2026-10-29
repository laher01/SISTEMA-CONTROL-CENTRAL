# S.P.T. — Sistema Pesquero de Trazabilidad

## Plataforma multiempresa para trazabilidad pesquera y operación documental

S.P.T. es la plataforma SaaS multiempresa (Multi-Tenant) del proyecto **Sistema Pesquero de Trazabilidad**. La plataforma administra operaciones de pesca, documentos y evidencias de forma trazable. Cada organización tiene su tenant independiente. **SNIDERFISH es el tenant piloto y plantilla; no es la plataforma.**

No es un sistema de facturación.

No es un ERP tradicional.

Su objetivo es hacer trazable cada operación pesquera desde el reporte de la embarcación hasta la descarga y recepción en planta, y conservar sus documentos, pesajes, responsables y movimientos de dinero en un expediente verificable.

---

# Objetivo

Registrar y auditar en un solo expediente:

• Reportes de armadores y confirmaciones del comprador.
• Descargas de muelle, traslado y recepción por vehículo en planta.
• Pesos declarados, de muelle y de planta, conservados por separado.
• Responsables, horarios previstos y reales.
• Documentos y evidencias de cada etapa.
• Gastos operativos, adelantos, reembolsos y devoluciones.
• Préstamos personales aislados de las operaciones.
• Factura adjunta y paquete de documentos listo para pago.

---

# Problemas que resuelve

Las operaciones y documentos suelen quedar dispersos entre:

- Correos electrónicos
- WhatsApp
- Carpetas compartidas
- PDF
- Imágenes
- Voucher
- Guías
- Formatos de descarga y actas

S.P.T. convierte esa información en expedientes y eventos de operación trazables.

---

# Arquitectura

S.P.T. está construido como una plataforma SaaS Multi-Tenant.

Cada tenant posee un espacio completamente independiente para administrar:

- Embarcaciones y actores
- Operaciones pesqueras
- Vehículos, muelles y plantas
- Usuarios
- Documentos
- Gastos y adelantos
- Evidencias
- Historial y reportes

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
- [`docs/PESCA_OPERACIONES.md`](docs/PESCA_OPERACIONES.md) — API inicial para descargas de muelle,
  recepción por vehículo en planta, evidencias e historial operativo.
- [`docs/futuro/`](docs/futuro/) — visión a largo plazo (NEXUS, agentes, infraestructura avanzada), fuera del alcance actual.

## Ejecución local del MVP

Para probar S.P.T. sin autenticación ni Docker:

- Windows: ejecuta `iniciar-local.cmd`.
- Linux/macOS: ejecuta `./iniciar-local.sh`.

El iniciador crea una base SQLite local, conserva los documentos en
`backend/storage_local` y abre la interfaz en `http://127.0.0.1:5173`.
PostgreSQL continúa siendo la base oficial para despliegues y validación de producción.

Para la instalación aislada en la VPS de pruebas, PostgreSQL persistente, OCR, Cloudflare Tunnel,
respaldos y despliegue automático desde GitHub, consulta [`deploy/README.md`](deploy/README.md).

La extracción de texto PDF funciona con las dependencias del backend. Para OCR de imágenes
debe instalarse Tesseract; el paquete de idioma español mejora el reconocimiento de documentos
peruanos. Los resultados OCR conservan motor, idioma y confianza y no se aplican como
clasificación definitiva sin confirmación humana.

---

# Filosofía

"No desarrollamos un software.

Construimos una plataforma inteligente capaz de comprender, organizar y controlar la documentación empresarial."
