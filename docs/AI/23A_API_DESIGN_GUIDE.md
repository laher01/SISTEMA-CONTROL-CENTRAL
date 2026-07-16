# 23A_API_DESIGN_GUIDE.md

# FACT CENTRAL

## API DESIGN GUIDE

### Guía Oficial de Diseño de APIs

---

# Objetivo

Definir los estándares oficiales para el diseño, desarrollo, evolución y mantenimiento de todas las APIs de FACT CENTRAL.

Este documento garantiza que todas las APIs sean consistentes, seguras, versionadas y fáciles de mantener.

---

# Filosofía

Las APIs son contratos.

No son simplemente funciones.

Una API bien diseñada puede mantenerse durante años sin romper la compatibilidad.

---

# Principios

Toda API deberá ser:

- consistente;
- predecible;
- segura;
- versionada;
- auditable;
- documentada;
- desacoplada;
- orientada a recursos.

---

# Convención de URLs

Siempre utilizar

```
/api/v1/
```

Ejemplos

```
GET /api/v1/companies

GET /api/v1/companies/{uuid}

POST /api/v1/documents

PUT /api/v1/documents/{uuid}

DELETE /api/v1/documents/{uuid}
```

Nunca utilizar

```
/createCompany

/getCompanies

/deleteDocument

/updateVoucher
```

---

# Recursos

Siempre utilizar sustantivos.

Correcto

```
companies

documents

payments

users

missions
```

Incorrecto

```
createCompany

payInvoice

newUser
```

---

# Métodos HTTP

GET

Consultar.

POST

Crear.

PUT

Actualizar completamente.

PATCH

Actualizar parcialmente.

DELETE

Eliminación lógica.

---

# UUID

Todas las entidades utilizarán UUID.

Ejemplo

```
GET

/api/v1/companies/550e8400-e29b-41d4-a716-446655440000
```

Nunca IDs secuenciales.

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

# Errores

Formato obligatorio

```
{
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Documento no encontrado.",
    "field": "document_id",
    "severity": "ERROR"
}
```

---

# Validaciones

Los errores de validación deberán indicar

campo;

valor;

regla;

mensaje.

Ejemplo

```
{
  "field":"ruc",
  "value":"123",
  "rule":"RUC_LENGTH",
  "message":"El RUC debe tener 11 dígitos."
}
```

---

# Versionado

Toda API tendrá versión.

Ejemplo

```
/api/v1/

/api/v2/
```

Nunca modificar una API existente de forma incompatible.

---

# Compatibilidad

Las nuevas versiones deberán mantener compatibilidad cuando sea posible.

Las versiones antiguas tendrán un período de convivencia antes de su retiro.

---

# Idempotencia

PUT

Debe ser idempotente.

PATCH

Debe modificar únicamente los campos enviados.

POST

Podrá crear nuevos recursos.

DELETE

Realizará eliminación lógica.

---

# Paginación

Formato estándar

```
?page=1&page_size=50
```

Respuesta

```
total

page

page_size

total_pages
```

---

# Ordenamiento

```
?sort=name

?sort=-created_at
```

---

# Filtros

Ejemplos

```
?status=ACTIVE

?company_id=

?date_from=

?date_to=
```

---

# Búsqueda

```
?search=AREVALO
```

---

# Archivos

Toda subida utilizará

multipart/form-data

Permitidos

PDF

PNG

JPG

JPEG

WEBP

TIFF

---

# Tamaño Máximo

Configurable.

Nunca codificado en el sistema.

---

# Operaciones Masivas

Ejemplo

```
POST

/api/v1/documents/bulk-upload
```

Respuesta

```
cantidad procesada

cantidad correcta

cantidad con errores

detalle
```

---

# Seguridad

HTTPS obligatorio.

JWT.

Refresh Token.

RBAC.

Rate Limit.

Validación de permisos.

Registro de auditoría.

---

# Auditoría

Toda petición registrará

usuario;

IP;

endpoint;

método;

duración;

resultado;

correlation_id.

---

# WebSockets

Se utilizarán para

Dashboard.

Progreso OCR.

Misiones.

Eventos.

Alertas.

Estado de Agentes.

---

# OpenAPI

Toda API deberá documentarse automáticamente mediante

Swagger.

OpenAPI.

Redoc.

---

# Convención de Nombres

Correcto

```
companies

documents

payments

missions

dashboard
```

Incorrecto

```
companyController

payInvoice

uploadDocumentNow
```

---

# Convención de Estados

Siempre utilizar valores estandarizados.

Ejemplo

```
ACTIVE

INACTIVE

PENDING

COMPLETED

FAILED

CANCELLED

ARCHIVED
```

---

# Performance

Toda consulta deberá:

paginar;

permitir filtros;

evitar consultas N+1;

utilizar índices.

---

# Observabilidad

Cada endpoint registrará

latencia;

errores;

uso;

cantidad de solicitudes;

consumo de recursos.

---

# Escalabilidad

Toda API deberá poder evolucionar sin romper contratos existentes.

---

# Checklist de Desarrollo

Antes de publicar un endpoint deberá verificarse:

✓ Documentado.

✓ Validado.

✓ Probado.

✓ Auditado.

✓ Versionado.

✓ Autorizado.

✓ Optimizado.

✓ Registrado en OpenAPI.

---

# Regla Suprema

Toda API de FACT CENTRAL deberá cumplir esta guía.

La consistencia en el diseño de las APIs es un requisito obligatorio para garantizar la mantenibilidad, interoperabilidad y evolución del Sistema Operativo Empresarial NEXUS.
