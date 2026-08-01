# 07_SAAS_MASTER_ARCHITECTURE.md

# FACT CENTRAL SaaS

## SAAS MASTER ARCHITECTURE

Versión 1.0

---

# 1. Objetivo

Definir la arquitectura maestra oficial de FACT CENTRAL SaaS.

Este documento integra:

- Tenants;
- Administradores;
- identidades;
- roles;
- permisos;
- suscripciones;
- facturación SaaS;
- seguridad;
- almacenamiento;
- procesamiento documental;
- FACT CENTRAL ERP;
- NEXUS;
- infraestructura;
- recuperación;
- escalabilidad;
- auditoría.

Este documento será la referencia principal para entender
cómo funciona toda la plataforma.

---

# 2. Definición oficial

FACT CENTRAL será una plataforma SaaS multi-tenant.

Cada suscripción crea un espacio de trabajo independiente
administrado por un Administrador Propietario.

Ese espacio podrá contener:

- múltiples Clientes/Receptores;
- múltiples Proveedores/Emisores;
- múltiples Usuarios;
- múltiples Gestores;
- Gerentes;
- Secretarías;
- documentos;
- expedientes;
- pedidos;
- productos;
- alertas;
- liquidaciones;
- pagos;
- configuraciones.

---

# 3. Regla principal del SaaS

La suscripción pertenece al Tenant.

El Tenant representa el espacio de trabajo del Administrador.

No representa:

- una empresa receptora;
- una empresa proveedora;
- un Cliente;
- un Usuario;
- un Gestor;
- una Factura;
- un Expediente.

Ejemplo:

FACT CENTRAL
↓
TENANT FC-A7K92M
↓
ADMINISTRADOR LUIS ARÉVALO
↓
CLIENTES + PROVEEDORES + USUARIOS + GESTORES + DOCUMENTOS

---

# 4. Arquitectura general

```text
USUARIO FINAL
      ↓
DOMINIO PRINCIPAL
      ↓
CLOUDFLARE / WAF / DDoS
      ↓
LOAD BALANCER
      ↓
API GATEWAY
      ↓
BACKEND FACT CENTRAL
      ↓
SERVICIOS DE NEGOCIO
      ↓
COLAS Y WORKERS
      ↓
POSTGRESQL + OBJECT STORAGE
      ↓
REPLICACIÓN + BACKUPS
      ↓
NEXUS + OBSERVABILIDAD
