# 22_DATABASE_SCHEMA.md

# FACT CENTRAL

## DATABASE SCHEMA

### Esquema Maestro de Base de Datos

---

# Objetivo

Definir la estructura oficial de PostgreSQL para FACT CENTRAL.

Este documento constituye el modelo físico de datos sobre el cual se implementará el ERP.

Toda tabla, vista, índice, función y relación deberá respetar este esquema.

---

# Filosofía

La Base de Datos no almacena únicamente información.

Almacena el conocimiento operativo de la organización.

Toda entidad deberá estar relacionada con el Expediente.

---

# Motor

PostgreSQL

Versión mínima

17

ORM

SQLAlchemy 2.x

Migraciones

Alembic

---

# Convenciones

Todas las tablas tendrán

uuid

created_at

updated_at

deleted_at

created_by

updated_by

organization_id

status

version

---

# Esquema General

```
auth

core

business

documents

finance

missions

ai

audit

dashboard

config
```

---

# Esquema AUTH

Tablas

usuarios

roles

permisos

usuarios_roles

sesiones

tokens

refresh_tokens

organizaciones

---

# Esquema CORE

Tablas

gestores

empresas

expedientes

estados

prioridades

tipos_documento

tipos_empresa

categorias

---

# Esquema DOCUMENTS

Tablas

documentos

facturas

guias

vouchers

rhe

retenciones

cotizaciones

correos

whatsapp

imagenes

ocr

json_ia

versiones

storage

hashes

---

# Esquema BUSINESS

Tablas

productos

detalle_productos

servicios

clientes

proveedores

contratos

observaciones

---

# Esquema FINANCE

Tablas

pagos

comisiones

liquidaciones

bancarizacion

detracciones

retenciones_financieras

movimientos

cuentas

---

# Esquema MISSIONS

Tablas

misiones

tareas

planes_accion

objetivos

estrategias

prioridades

recursos

resultados

---

# Esquema AI

Tablas

memoria

knowledge_nodes

knowledge_edges

contextos

razonamientos

decisiones

aprendizajes

eventos

agentes

prompts

modelos

metricas_ia

---

# Esquema AUDIT

Tablas

auditoria

logs

historial

eventos_sistema

errores

alertas

versiones

---

# Esquema DASHBOARD

Tablas

indicadores

kpis

estadisticas

cache_dashboard

resumenes

---

# Esquema CONFIG

Tablas

configuracion

variables

integraciones

api_keys

plantillas

catalogos

---

# Relaciones

```
Usuario

↓

Gestor

↓

Empresa

↓

Expediente

↓

Documento

↓

Producto

↓

Pago

↓

Misión

↓

Auditoría
```

---

# Claves Primarias

Todas las tablas utilizarán UUID.

Nunca IDs secuenciales como clave principal.

---

# Claves Foráneas

Toda relación utilizará claves foráneas.

Nunca existirán relaciones implícitas.

---

# Índices

Se crearán índices para

UUID

RUC

HASH

Serie

Correlativo

Fecha

Empresa

Expediente

Gestor

Estado

Tipo Documento

Misión

Evento

---

# Restricciones

Toda tabla deberá validar

NOT NULL

UNIQUE

CHECK

FOREIGN KEY

DEFAULT

---

# Eliminación

Toda eliminación será lógica.

deleted_at

deleted_by

delete_reason

---

# Versionado

Toda entidad importante tendrá

version

parent_version

change_reason

---

# Historial

Toda modificación importante generará

Historial.

Auditoría.

Evento.

---

# Storage

La Base de Datos únicamente almacenará

Metadatos.

Nunca PDFs.

Nunca imágenes.

Nunca archivos binarios.

---

# Integridad

Toda operación deberá garantizar

Consistencia.

Atomicidad.

Aislamiento.

Durabilidad.

---

# Escalabilidad

Diseñada para

Más de 100 millones de registros.

Millones de documentos.

Miles de empresas.

Miles de usuarios.

Décadas de información.

---

# Backups

Respaldos

Incrementales.

Diarios.

Semanales.

Mensuales.

---

# Optimización

Particionamiento.

Índices.

Materialized Views.

Consultas optimizadas.

Cache.

---

# Regla Suprema

Toda la información de FACT CENTRAL deberá almacenarse respetando este esquema.

El Expediente constituye el eje principal de toda la Base de Datos.

Ninguna entidad crítica podrá existir sin trazabilidad, auditoría y relaciones claramente definidas.
