# 26A_INFRASTRUCTURE_TOPOLOGY.md

# FACT CENTRAL

## INFRASTRUCTURE TOPOLOGY

### Topología Oficial de Infraestructura de NEXUS

Versión 1.0

---

# Objetivo

Definir la topología física y lógica de la infraestructura que soportará FACT CENTRAL.

Este documento describe cómo se distribuyen los servicios, servidores, redes, almacenamiento y componentes de NEXUS en los distintos escenarios de operación.

---

# Filosofía

La infraestructura debe crecer sin modificar el software.

NEXUS deberá poder operar:

- desde una laptop;
- en un servidor local;
- en un VPS;
- en la nube;
- en un clúster empresarial.

La arquitectura será escalable desde el primer día.

---

# Principios

Toda infraestructura deberá ser:

- modular;
- desacoplada;
- segura;
- observable;
- redundante;
- escalable;
- automatizable.

---

# Arquitectura General

```
Usuarios

↓

Internet

↓

DNS

↓

Cloudflare

↓

Firewall

↓

Reverse Proxy

↓

API Gateway

↓

NEXUS

↓

Motores

↓

Agentes

↓

Base de Datos

↓

Storage

↓

Backups
```

---

# Topología Inicial

```
┌─────────────────────────────┐
│         INTERNET            │
└──────────────┬──────────────┘
               │
         Cloudflare
               │
          Firewall
               │
            Nginx
               │
      ┌────────┴────────┐
      │                 │
 Frontend         Backend
 (React)          (FastAPI)
      │                 │
      └────────┬────────┘
               │
             NEXUS
               │
 ┌─────────────┼─────────────┐
 │             │             │
Motores     Agentes      Scheduler
 │             │             │
 └─────────────┼─────────────┘
               │
             Redis
               │
          PostgreSQL
               │
            Storage
               │
            Backups
```

---

# Segmentos

## Segmento Público

Cloudflare

DNS

HTTPS

Frontend

---

## Segmento Aplicación

FastAPI

Motores

Agentes

Scheduler

Workers

---

## Segmento Datos

PostgreSQL

Redis

Storage

Backups

Nunca será accesible desde Internet.

---

## Segmento Administración

Monitoreo

Grafana

Prometheus

Logs

Sentry

Acceso restringido.

---

# Escenario 1

## Desarrollo Local

```
Laptop

↓

Docker Desktop

↓

Frontend

Backend

Redis

PostgreSQL

Storage
```

Uso

Desarrollo.

Pruebas.

Debug.

---

# Escenario 2

## Servidor Local

```
LAN

↓

Servidor Principal

↓

Nginx

↓

Backend

↓

PostgreSQL

↓

Storage
```

Uso

Empresa pequeña.

---

# Escenario 3

## VPS

```
Internet

↓

Cloudflare

↓

VPS

↓

Docker

↓

Frontend

Backend

Redis

PostgreSQL
```

Uso

Producción inicial.

---

# Escenario 4

## Cloud

```
Cloudflare

↓

Load Balancer

↓

Backend x N

↓

Redis Cluster

↓

PostgreSQL Cluster

↓

Object Storage
```

Uso

Miles de usuarios.

---

# Escenario 5

## Arquitectura Empresarial

```
Internet

↓

Cloudflare

↓

Firewall

↓

Load Balancer

↓

API Gateway

↓

Backend Cluster

↓

NEXUS Cluster

↓

Redis Cluster

↓

Kafka

↓

PostgreSQL Cluster

↓

Storage Cluster

↓

Backups
```

Uso

Alta disponibilidad.

---

# Redes

Separación lógica:

DMZ

Aplicación

Base de Datos

Administración

Backups

---

# Balanceo

Permitirá distribuir:

Usuarios.

APIs.

OCR.

IA.

Misiones.

Reportes.

---

# Workers

Cada Worker ejecutará tareas específicas.

Ejemplo

Worker OCR

Worker IA

Worker Scheduler

Worker Reportes

Worker Notificaciones

Worker Integraciones

---

# GPU

Los modelos IA podrán ejecutarse en servidores con GPU independientes.

No dependerán del Backend.

---

# Almacenamiento

```
Storage

├── documents/
├── images/
├── ocr/
├── json/
├── reports/
├── backups/
├── temp/
└── versions/
```

---

# Integraciones

Servicios externos:

SUNAT

APIPERU

OpenAI

Correo

WhatsApp

Google Drive

Cloudflare

Todos mediante HTTPS.

---

# Alta Disponibilidad

Permitirá:

Múltiples Backends.

Replicación PostgreSQL.

Redis Sentinel.

Storage redundante.

Failover.

---

# Recuperación

Ante una falla:

Detectar.

Aislar.

Reemplazar.

Reiniciar.

Notificar.

Registrar.

---

# Observabilidad

Todos los componentes expondrán métricas.

CPU.

RAM.

Disco.

Red.

Errores.

Eventos.

Latencia.

---

# Seguridad

Firewall.

VPN.

HTTPS.

TLS.

JWT.

Cloudflare.

Segmentación de red.

Backups cifrados.

---

# Escalabilidad

Se podrá pasar de:

1 servidor

↓

3 servidores

↓

10 servidores

↓

Clúster

Sin modificar el código del ERP.

---

# Roadmap

Nivel 1

Laptop.

Nivel 2

Servidor Local.

Nivel 3

VPS.

Nivel 4

Cloud.

Nivel 5

Cluster Empresarial.

---

# Integración

Este documento complementa:

- 20_BACKEND_IMPLEMENTATION_PLAN.md
- 21_FRONTEND_IMPLEMENTATION_PLAN.md
- 22_DATABASE_SCHEMA.md
- 25_AGENT_CATALOG.md
- 26_DEPLOYMENT_ARCHITECTURE.md
- 27_SECURITY_ARCHITECTURE.md

---

# Regla Suprema

La infraestructura de FACT CENTRAL deberá ser independiente del entorno donde se despliegue.

NEXUS deberá ejecutarse de forma consistente en cualquier plataforma compatible, manteniendo la misma arquitectura lógica, los mismos principios de seguridad y la misma capacidad de escalar desde un entorno local hasta una infraestructura empresarial distribuida.
