# 23_API_CONTRACTS.md

# FACT CENTRAL

## API CONTRACTS

### Contratos Oficiales de la API

---

# Objetivo

Definir el estándar oficial para todas las APIs de FACT CENTRAL.

Todo servicio interno o externo deberá respetar estos contratos.

Las APIs representan el lenguaje oficial entre:

- Frontend
- Backend
- NEXUS
- Agentes
- Integraciones externas

---

# Filosofía

Las APIs no representan código.

Representan contratos.

Un contrato nunca debe romperse.

Las versiones deberán garantizar compatibilidad.

---

# Arquitectura

```
Cliente

↓

API Gateway

↓

Authentication

↓

Authorization

↓

Validation

↓

Controllers

↓

Services

↓

Motores

↓

Agentes

↓

Repositories

↓

PostgreSQL
```

---

# Estándares

Formato

JSON

Codificación

UTF-8

Protocolo

HTTPS

Versión

/api/v1/

Futuras versiones

/api/v2/

---

# Estructura Base

Toda petición incluirá

Authorization

Bearer Token

Content-Type

application/json

Accept

application/json

X-Correlation-ID

Organization-ID

---

# Respuesta Estándar

```
{
    "success": true,
    "message": "",
    "data": {},
    "errors": [],
    "warnings": [],
    "metadata": {
        "request_id": "",
        "correlation_id": "",
        "execution_time": "",
        "version": "1.0"
    }
}
```

---

# Códigos HTTP

200 OK

201 Created

204 No Content

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error

429 Too Many Requests

500 Internal Error

503 Service Unavailable

---

# Recursos Principales

/auth

/users

/roles

/companies

/expedients

/documents

/products

/payments

/missions

/events

/dashboard

/settings

/agents

/ai

/reports

/storage

/audit

---

# Ejemplo

GET

/api/v1/companies

POST

/api/v1/documents

PUT

/api/v1/expedients/{uuid}

DELETE

/api/v1/users/{uuid}

---

# Autenticación

JWT

Refresh Token

Tiempo configurable

Revocación

Sesiones activas

---

# Autorización

RBAC

Roles

Permisos

Organización

Propietario

Gestor

---

# Paginación

page

page_size

total

total_pages

next

previous

---

# Filtros

Todos los endpoints deberán permitir

Buscar

Ordenar

Filtrar

Paginar

---

# Auditoría

Toda petición registrará

Usuario

IP

Hora

Endpoint

Método

Duración

Resultado

---

# Versionado

Toda API tendrá

Versión

Estado

Fecha

Compatibilidad

---

# WebSocket

Se utilizará para

Dashboard

Eventos

OCR

Misiones

Notificaciones

Agentes

---

# Eventos

Las APIs podrán generar eventos

DOCUMENT_CREATED

EXPEDIENT_UPDATED

MISSION_COMPLETED

PAYMENT_REGISTERED

LEARNING_APPROVED

---

# Integraciones

SUNAT

APIPERU

OpenAI

Cloudflare

Correo

WhatsApp

Google Drive

---

# Seguridad

HTTPS obligatorio

JWT

Rate Limit

CORS

CSRF

Validaciones

Sanitización

Logs

---

# Observabilidad

Cada endpoint registrará

Tiempo

Errores

Cantidad de llamadas

Consumo

Latencia

---

# Escalabilidad

Preparada para

Microservicios

Gateway

Balanceadores

Alta disponibilidad

---

# Documentación

Toda API deberá generarse automáticamente mediante

OpenAPI

Swagger

Redoc

---

# Regla Suprema

Toda comunicación con FACT CENTRAL deberá realizarse mediante APIs documentadas, versionadas, auditables y compatibles hacia atrás.

Las APIs constituyen el contrato oficial entre todos los componentes del ecosistema.
