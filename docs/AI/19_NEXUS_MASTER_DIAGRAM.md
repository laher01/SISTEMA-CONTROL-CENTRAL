# 19_NEXUS_MASTER_DIAGRAM.md

# FACT CENTRAL

# NEXUS MASTER DIAGRAM

## Diagrama Maestro de Arquitectura

---

# Objetivo

El presente documento describe el funcionamiento integral de FACT CENTRAL desde la entrada de información hasta la generación de inteligencia ejecutiva.

Representa el mapa oficial de funcionamiento del Sistema Operativo Empresarial NEXUS.

Toda nueva funcionalidad deberá integrarse respetando esta arquitectura.

---

# Visión General

```
                            USUARIOS
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
 Administrador             Secretaría               Gestores
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                          FRONTEND (React)
                                 │
                          API Gateway (FastAPI)
                                 │
                         Authentication Layer
                                 │
                         Authorization Layer
                                 │
                         Validation Layer
                                 │
                          NEXUS OPERATING SYSTEM
```

---

# Núcleo de NEXUS

```
Memory System
        │
Knowledge Graph
        │
State Engine
        │
Event Bus
        │
Event Router
        │
Scheduler
        │
Context Engine
        │
Reasoning Engine
        │
Decision Engine
        │
Action Planner
        │
Execution Engine
        │
Operational Quality Engine
        │
Continuous Learning System
```

---

# Núcleo Estratégico

```
Goal Engine
       │
Strategy Engine
       │
Priority Engine
       │
Resource Engine
       │
Orchestration Engine
       │
Executive Intelligence Engine
```

---

# Multi-Agent System

```
Agente OCR

Agente Documental

Agente Expedientes

Agente Tributario

Agente Financiero

Agente Comercial

Agente Dashboard

Agente Auditor

Agente IA

Agente Seguridad

Agente API

Agente Notificaciones

Agente Reportes

Agente Aprendizaje
```

---

# Flujo Documental

```
Archivo recibido

↓

Storage

↓

OCR

↓

Clasificación IA

↓

Extracción de datos

↓

Validación

↓

Empresa

↓

Expediente

↓

Relaciones

↓

Base de Datos

↓

Dashboard

↓

Auditoría
```

---

# Flujo Cognitivo

```
Documento

↓

Contexto

↓

Razonamiento

↓

Decisión

↓

Plan

↓

Ejecución

↓

Calidad

↓

Aprendizaje
```

---

# Flujo Estratégico

```
Objetivo

↓

Estrategia

↓

Prioridad

↓

Recursos

↓

Orquestación

↓

Misiones

↓

Resultados

↓

Inteligencia Ejecutiva
```

---

# Flujo de Eventos

```
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

# Flujo del Expediente

```
Empresa

↓

Expediente

↓

Documentos

↓

Productos

↓

Pagos

↓

Estados

↓

Indicadores

↓

Historial

↓

Cierre

↓

Aprendizaje
```

---

# Base de Datos

```
PostgreSQL

│

Usuarios

Roles

Gestores

Empresas

Expedientes

Documentos

Productos

Pagos

Misiones

Eventos

Auditoría

Configuración
```

---

# Almacenamiento

```
Storage

│

PDF

Imágenes

Correos

WhatsApp

OCR

JSON

Versiones

Backups
```

---

# Servicios Externos

```
SUNAT

↓

APIPERU

↓

OpenAI

↓

Cloudflare

↓

Correo

↓

WhatsApp

↓

Google Drive (opcional)

↓

Otros proveedores
```

---

# Dashboard

Mostrará en tiempo real:

- estado del sistema;
- expedientes;
- empresas;
- documentos;
- pagos;
- objetivos;
- estrategias;
- recursos;
- indicadores;
- alertas;
- recomendaciones.

---

# Seguridad

Todas las capas deberán respetar:

- autenticación;
- autorización;
- permisos;
- organizaciones;
- auditoría;
- trazabilidad.

---

# Observabilidad

Todo el sistema deberá responder:

- ¿Qué ocurrió?
- ¿Quién lo hizo?
- ¿Cuándo ocurrió?
- ¿Qué motor participó?
- ¿Qué agente ejecutó?
- ¿Qué evento lo originó?
- ¿Cuál fue el resultado?

---

# Escalabilidad

La arquitectura permitirá incorporar:

- nuevos motores;
- nuevos agentes;
- nuevos módulos;
- nuevos servicios;
- nuevos países;
- nuevas empresas;
- nuevos modelos de IA.

Sin modificar el núcleo de NEXUS.

---

# Arquitectura Física

```
Usuarios
     │
Internet
     │
Cloudflare
     │
Nginx
     │
FastAPI
     │
NEXUS OS
     │
Multi-Agent System
     │
PostgreSQL
     │
Storage
     │
Backups
```

---

# Arquitectura Lógica

```
Presentación

↓

Servicios

↓

Motores

↓

Agentes

↓

Eventos

↓

Persistencia

↓

Infraestructura
```

---

# Regla Suprema

Toda interacción dentro de FACT CENTRAL deberá respetar el flujo definido en este documento.

El NEXUS MASTER DIAGRAM constituye el mapa oficial de funcionamiento del Sistema Operativo Empresarial.

Toda nueva funcionalidad deberá integrarse respetando esta arquitectura.
