# Esquema de datos del MVP

Fuente única de verdad del modelo físico del MVP. La implementación
(SQLAlchemy + migraciones Alembic) vive en `backend/`.
`DATA_MODEL.md`, `DATABASE_ARCHITECTURE.md` y `AI/22_DATABASE_SCHEMA.md`
describen la visión completa a largo plazo.

## Convenciones

- Clave primaria `id` UUID en todas las tablas.
- Toda tabla de negocio tiene `tenant_id` (FK a `tenants`). Nunca `organization_id`.
- `created_at` / `updated_at` en UTC. Eliminación lógica con `deleted_at`.
- Montos `NUMERIC(14,2)`. RUC `VARCHAR(11)`.
- La base de datos guarda metadatos; los archivos van al storage.

## Tablas

### tenants
| columna | tipo | notas |
|---|---|---|
| id | uuid | PK |
| nombre | varchar(200) | único |
| created_at | timestamptz | |

### empresas
| columna | tipo | notas |
|---|---|---|
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| ruc | varchar(11) | único por tenant |
| razon_social | varchar(300) | |
| autorizada | boolean | "trabaja con nosotros" (default false) |
| agente_retencion | boolean | default false |
| created_at, updated_at, deleted_at | timestamptz | |

### gestores
| columna | tipo | notas |
|---|---|---|
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| codigo | varchar(50) | único por tenant (ej. `WILLI01`) |
| nombre | varchar(200) | |
| created_at, deleted_at | timestamptz | |

### expedientes
| columna | tipo | notas |
|---|---|---|
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| receptor_id | uuid | FK empresas |
| emisor_id | uuid | FK empresas |
| tipo_comprobante | varchar(4) | `FACT` \| `RHE` |
| serie | varchar(4) | |
| correlativo | varchar(8) | sin ceros a la izquierda |
| fecha_emision | date | |
| moneda | varchar(3) | `PEN` \| `USD` |
| importe_total | numeric(14,2) | |
| requiere_guia | boolean | default true (false para servicios/RHE) |
| gestor_id | uuid | FK gestores, nullable |
| estado | varchar(10) | `VERDE` \| `AMARILLO` \| `NARANJA` \| `ROJO` |
| pendiente_aprobacion | boolean | receptor no autorizado |
| created_at, updated_at, deleted_at | timestamptz | |

Único: `(tenant_id, receptor_id, tipo_comprobante, serie, correlativo, emisor_id)`.

### documentos
| columna | tipo | notas |
|---|---|---|
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| expediente_id | uuid | FK expedientes, nullable mientras está en el Área General |
| tipo_documento | varchar(6) | `FACT RHE GRR GRT VCHR RET EMAIL WSP COT OC REQ FOTO OTRO`, nullable |
| estado | varchar(30) | `PENDIENTE_CLASIFICACION` \| `PENDIENTE_RELACION` \| `RELACIONADO` |
| sha256 | char(64) | único por tenant |
| nombre_original | varchar(500) | |
| mime_type | varchar(100) | |
| tamano_bytes | bigint | |
| ruta_storage | varchar(500) | |
| datos_extraidos | jsonb | nullable |
| gestor_id | uuid | FK gestores, nullable |
| created_at, deleted_at | timestamptz | |

### alertas
| columna | tipo | notas |
|---|---|---|
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| expediente_id | uuid | FK expedientes |
| tipo | varchar(40) | `BANCARIZACION_SIN_VOUCHER` \| `RETENCION_PENDIENTE` \| `RECEPTOR_NO_AUTORIZADO` \| `EXPEDIENTE_VENCIDO` |
| mensaje | varchar(500) | |
| resuelta | boolean | |
| created_at, resuelta_at | timestamptz | |

Único: `(expediente_id, tipo)`.

### auditoria
| columna | tipo | notas |
|---|---|---|
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| accion | varchar(60) | ej. `DOCUMENTO_SUBIDO` |
| entidad | varchar(40) | |
| entidad_id | uuid | |
| datos | jsonb | |
| created_at | timestamptz | |
