# 23B_API_STYLE_GUIDE.md

# FACT CENTRAL

## API STYLE GUIDE

### Guía Oficial de Estilo para el Desarrollo de APIs

---

# Objetivo

Establecer un estándar único para el desarrollo de todas las APIs de FACT CENTRAL.

Esta guía define la estructura, organización, nomenclatura y buenas prácticas que deberán seguir todos los desarrolladores del proyecto.

---

# Filosofía

El código debe ser:

- consistente;
- legible;
- mantenible;
- desacoplado;
- reutilizable;
- testeable.

La calidad del código tiene prioridad sobre la velocidad de desarrollo.

---

# Principios

Toda API deberá cumplir:

- Single Responsibility Principle
- SOLID
- DRY
- KISS
- Clean Code
- Clean Architecture

---

# Arquitectura

Toda funcionalidad seguirá la siguiente estructura.

```
Router

↓

Controller

↓

Service

↓

Engine (si aplica)

↓

Repository

↓

PostgreSQL
```

Nunca un Router accederá directamente al Repository.

Nunca un Repository contendrá lógica de negocio.

---

# Organización

Ejemplo

```
companies/

router.py

controller.py

service.py

repository.py

schemas.py

models.py

validators.py

events.py

exceptions.py

constants.py

README.md

tests/
```

---

# Router

Responsabilidad

- definir endpoints;
- recibir solicitudes;
- validar autenticación;
- invocar Controllers.

Nunca deberá contener lógica empresarial.

---

# Controller

Responsabilidad

- interpretar la solicitud;
- validar parámetros;
- llamar al Service correspondiente;
- construir la respuesta.

---

# Service

Responsabilidad

Toda la lógica de negocio.

Aquí se implementarán:

- reglas;
- validaciones;
- procesos;
- coordinación con motores;
- coordinación con agentes.

---

# Repository

Responsabilidad

Acceder exclusivamente a PostgreSQL.

Nunca contendrá reglas del negocio.

---

# Schemas

Todos los DTO deberán implementarse con

Pydantic v2.

Separar

Create

Update

Read

Response

Filters

---

# Models

Todos los modelos utilizarán

SQLAlchemy 2.x

No mezclar modelos ORM con Schemas.

---

# Validaciones

Crear un archivo

validators.py

Toda validación compleja deberá implementarse allí.

---

# Eventos

Cada módulo podrá publicar eventos mediante

events.py

Nunca publicar eventos directamente desde el Router.

---

# Excepciones

Crear

exceptions.py

Todas las excepciones personalizadas deberán centralizarse.

Ejemplo

CompanyNotFound

InvalidDocument

DuplicatedInvoice

PermissionDenied

---

# Constantes

Crear

constants.py

Nunca utilizar textos repetidos dentro del código.

---

# Dependencias

Utilizar Dependency Injection.

Ejemplo

```
Depends(...)
```

Nunca instanciar servicios manualmente dentro del Router.

---

# Nombres

Funciones

snake_case

Variables

snake_case

Clases

PascalCase

Constantes

UPPER_CASE

Archivos

snake_case.py

---

# Endpoints

Correcto

```
GET

/companies

POST

/companies

GET

/companies/{uuid}

PATCH

/companies/{uuid}

DELETE

/companies/{uuid}
```

Incorrecto

```
/getCompany

/createCompany

/updateCompany

/removeCompany
```

---

# Responses

Toda respuesta utilizará el Response Standard.

Nunca devolver diccionarios improvisados.

---

# Logging

Nunca usar

print()

Siempre utilizar el sistema oficial de logs.

---

# Manejo de Errores

Nunca utilizar

```
except:
```

Siempre capturar excepciones específicas.

Registrar:

usuario

endpoint

motor

error

correlation_id

---

# Transacciones

Toda operación crítica utilizará transacciones.

Rollback automático.

---

# Seguridad

Nunca confiar en datos enviados por el cliente.

Toda autorización deberá verificarse en el Backend.

---

# Performance

Evitar

Consultas N+1.

Loops innecesarios.

Duplicidad de consultas.

Preferir operaciones en lote.

---

# Testing

Cada módulo deberá contener

tests/

Pruebas

Unitarias

Integración

Seguridad

Performance

---

# Documentación

Todo módulo deberá contener

README.md

Explicando

objetivo

dependencias

eventos

API

casos de uso

---

# Ejemplo de Flujo

```
Cliente

↓

Router

↓

Controller

↓

Service

↓

Reasoning Engine

↓

Repository

↓

PostgreSQL

↓

Service

↓

Controller

↓

Router

↓

Cliente
```

---

# Checklist

Antes de aprobar una API verificar:

✓ Endpoint documentado.

✓ Schemas definidos.

✓ Validaciones implementadas.

✓ Permisos revisados.

✓ Eventos publicados.

✓ Tests aprobados.

✓ Logs registrados.

✓ Auditoría funcionando.

✓ Respuesta estándar.

✓ Código revisado.

---

# Integración con NEXUS

Toda API deberá poder interactuar con:

- Event Bus;
- Event Router;
- Scheduler;
- Motores;
- Agentes;
- Auditoría;
- Dashboard;
- Executive Intelligence.

---

# Regla Suprema

Toda API desarrollada para FACT CENTRAL deberá seguir esta guía de estilo.

La uniformidad del código es un requisito obligatorio para garantizar la calidad, mantenibilidad, escalabilidad y evolución del Sistema Operativo Empresarial NEXUS.
