# S.P.T. — Sistema Pesquero de Trazabilidad

## Identidad del producto

La plataforma es S.P.T. y opera con tenants independientes. **SNIDERFISH es el tenant piloto y
plantilla**, no la plataforma. Los planes y referencias históricas de este documento describen
componentes de la plataforma; el flujo pesquero activo se detalla en
[`docs/PESCA_OPERACIONES.md`](docs/PESCA_OPERACIONES.md).

## Plataforma SaaS multiempresa para trazabilidad de operaciones pesqueras

---

# MASTER PLAN

Versión: 3.0

Estado: Implementación del flujo operativo pesquero MVP

Última actualización: Octubre 2026

---

# MISIÓN

Construir S.P.T., una plataforma multiempresa que registre y relacione cada operación pesquera desde el reporte del armador hasta la recepción en planta, conservando responsables, tiempos, pesajes, gastos, documentos y evidencias sin mezclar tenants.

---

# VISIÓN

Hacer de S.P.T. una plataforma confiable para la trazabilidad pesquera, preparada para servir a múltiples tenants. SNIDERFISH funciona como piloto y plantilla; los nuevos tenants conservarán sus operaciones y configuración de forma independiente.

---

# FILOSOFÍA DEL PROYECTO

Antes de escribir una sola línea de código se debe:

1. Diseñar.
2. Documentar.
3. Validar.
4. Programar.
5. Probar.
6. Publicar.
7. Medir.
8. Mejorar.

Toda nueva funcionalidad deberá quedar completamente documentada antes de comenzar su desarrollo.

---

# NATURALEZA DEL PRODUCTO

S.P.T. no es un facturador.

S.P.T. no reemplaza por sí solo un ERP tradicional.

S.P.T. es la plataforma de trazabilidad pesquera. Incluye herramientas documentales para relacionar las evidencias de cada etapa.

Su objetivo es mostrar quién reportó, confirmó, descargó, transportó, recibió y registró cada movimiento, junto con el soporte correspondiente.

---

# OBJETIVOS PRINCIPALES

• Registrar el reporte, la preparación, la descarga, el traslado y la recepción de pesca.

• Conservar separados el peso declarado, el peso de muelle y el peso aceptado en planta.

• Relacionar documentos y evidencias con la operación, el vehículo y la embarcación correspondientes.

• Registrar gastos, adelantos, reembolsos y devoluciones con saldos auditables.

• Mantener los préstamos personales separados de la operación y su liquidación.

• Registrar el expediente y la factura lista para presentar a pago.

• Mantener trazabilidad completa de cada cambio, documento y responsable.

---

# PRINCIPIOS DEL SISTEMA

## 1. Arquitectura SaaS Multi-Tenant

Cada Administrador posee un espacio completamente aislado.

Toda la información pertenece al Tenant.

Nunca existe mezcla entre organizaciones.

---

## 2. Administración por Administrador

El Tenant pertenece al Administrador.

Un Administrador puede controlar:

• una empresa

• diez empresas

• cien empresas

• miles de proveedores

Todo dentro de un único Tenant.

---

## 3. Gestión de operaciones pesqueras y evidencias

El MVP prioriza el ciclo de descarga y recepción pesquera. La emisión de facturas, pagos y liquidaciones quedan fuera hasta definir e implementar sus reglas.

---

## 4. Clientes (Receptores)

Los clientes únicamente pueden ser creados por:

• Administrador

• Gerente

Nunca por Usuarios.

Nunca por Gestores.

---

## 5. Proveedores

Los proveedores pueden ser incorporados por:

• Usuarios

• Gestores

Siguiendo las reglas de validación establecidas.

---

## 6. Todo documento genera trazabilidad

Todo documento recibido conserva:

Origen

Usuario

Gestor

Fecha

Hora

Canal

Historial

Auditoría

---

## 7. Todo documento pertenece a un expediente

No existen documentos aislados.

Cada documento termina formando parte de un expediente digital.

---

# FLUJO GENERAL

Gestor

↓

Usuario

↓

Centro de Ingesta Documental

↓

Motor IA

↓

Motor de Reglas

↓

Motor de Expedientes

↓

Motor de Evidencias

↓

Dashboards

↓

Auditoría

---

# MOTORES PRINCIPALES

Motor de Ingesta Documental

Motor de Clasificación Inteligente

Motor de Reglas

Motor de Expedientes

Motor de Evidencias

Motor de Productos y Servicios

Motor de Pedidos

Motor de Distribución

Motor de Pagos

Motor Tributario

Motor de Alertas

Motor de Reportes

Motor de Inteligencia Ejecutiva

---

# ARQUITECTURA FUNCIONAL

Administrador

↓

Gerente

↓

Usuario

↓

Gestor

↓

Documentos

↓

Expedientes

↓

Dashboards

---

# INFRAESTRUCTURA OBJETIVO

Frontend

Cloudflare Pages

Backend

FastAPI

Base de Datos

PostgreSQL

Cache

Redis

IA

OpenAI

Almacenamiento

Object Storage

Replicación

Multi Nodo

Contenedores

Docker

Proxy

Nginx

Seguridad

Cloudflare

JWT

HTTPS

RBAC

Git

GitHub

CI/CD

GitHub Actions

---

# ESTADO DEL PROYECTO

| Área | Estado |
|---|---|
| Visión y reglas de negocio | Documentadas |
| Arquitectura | Documentada, pendiente de validar con implementación |
| Alcance del MVP | Definido en `docs/MVP.md` |
| Esquema de datos MVP | Definido en `docs/ESQUEMA_MVP.md` |
| Backend MVP | En desarrollo |
| Frontend | Pendiente |
| Testing | Pendiente |

Una arquitectura solo se considera validada cuando ha sido implementada y probada con datos reales.

---

# ROADMAP GENERAL

FASE 1 — Arquitectura y documentación: ✔

FASE 2 — MVP backend (ingesta, duplicados, expedientes, alertas, dashboard API): en curso

FASE 3 — Validación con documentos reales de 1–2 empresas: pendiente

FASE 4 — Autenticación, roles y frontend: pendiente

FASE 5 — OCR/IA, pagos a gestores, integraciones: pendiente

FASE 6 — Multi-tenant real y producción SaaS: pendiente

FASE 7 — NEXUS y capacidades avanzadas (`docs/futuro/`): pendiente

---

# DOCUMENTACIÓN MAESTRA

Este documento constituye la guía principal del proyecto.

Todos los documentos contenidos en:

/docs

deberán mantener coherencia con los principios, arquitectura y objetivos definidos en este MASTER PLAN.

Cualquier modificación importante en la arquitectura del sistema deberá reflejarse primero en este documento antes de implementarse en el resto de la documentación técnica.

---

# S.P.T. — SISTEMA PESQUERO DE TRAZABILIDAD

"Construimos una plataforma que registra y conecta cada etapa de la operación pesquera, desde el reporte hasta la recepción en planta."
