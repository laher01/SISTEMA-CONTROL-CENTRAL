# FACT CENTRAL

## Plataforma SaaS Inteligente para Gestión Documental Tributaria, Expedientes Digitales y Control Integral de Compras Empresariales

---

# MASTER PLAN

## Etapa 7 — Infraestructura, versiones y despliegues

En desarrollo por autorización del propietario el 2026-10-09.
Diagnóstico, diseño y estado verificable: `docs/ETAPA_7_INFRAESTRUCTURA.md`.
Se preserva el plan histórico; sus porcentajes no representan el código actual.

Versión: 2.0

Estado: Arquitectura Funcional (Pre-Desarrollo)

Última actualización: Agosto 2026

---

# MISIÓN

Construir la plataforma SaaS más completa para la administración documental de compras empresariales, permitiendo que empresas de cualquier tamaño controlen digitalmente toda su documentación tributaria mediante inteligencia artificial, expedientes digitales y procesos completamente trazables.

---

# VISIÓN

Convertir FACT CENTRAL en el estándar latinoamericano para la gestión documental tributaria, auditoría preventiva y control inteligente de compras empresariales, ofreciendo una plataforma escalable, segura y preparada para operar con miles de empresas simultáneamente.

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

FACT CENTRAL NO es un sistema de facturación.

FACT CENTRAL NO reemplaza a un ERP tradicional.

FACT CENTRAL es una plataforma SaaS especializada en la administración documental de procesos de compras empresariales.

Su objetivo es transformar miles de documentos dispersos en expedientes digitales inteligentes completamente relacionados.

---

# OBJETIVOS PRINCIPALES

• Centralizar toda la documentación tributaria de compras.

• Automatizar la creación de expedientes digitales.

• Relacionar automáticamente documentos pertenecientes a una misma operación comercial.

• Facilitar auditorías tributarias.

• Reducir riesgos documentarios.

• Generar inteligencia empresarial basada en compras.

• Automatizar procesos mediante IA.

• Mantener trazabilidad completa de cada documento.

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

## 3. Gestión exclusiva de Compras

La versión inicial administra únicamente procesos documentarios de compras.

Las ventas quedan previstas para futuras versiones.

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

# FACT CENTRAL

"No desarrollamos un software.

Construimos una plataforma inteligente capaz de comprender, organizar y controlar la documentación empresarial."
