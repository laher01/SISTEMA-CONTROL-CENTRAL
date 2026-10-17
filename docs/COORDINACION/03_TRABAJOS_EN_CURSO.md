# Trabajos en curso y reserva de áreas

**Verificar antes de usar:** este archivo no reemplaza Issues, PR y ramas recientes.

| ID | Trabajo | Área | Responsable | Estado | Rama / PR | Archivos previstos |
| --- | --- | --- | --- | --- | --- | --- |
| COORD-001 | Crear Centro de Coordinación | Coordinación | Chat arquitectura SaaS | INTEGRADO (confirmar despliegue) | `AGENTS.md`, `docs/COORDINACION/**` | `AGENTS.md`, `docs/COORDINACION/**` |
| SAAS-001 | Consola SUPERADMIN consulta integral solo lectura | SaaS | Chat arquitectura SaaS | PROPUESTO | Sin rama | Backend/frontend SUPERADMIN (por identificar) |
| SAAS-002 | Auditoría de aislamiento cross-tenant | Seguridad | Chat arquitectura SaaS | PROPUESTO | Sin rama | Servicios API, autenticación, tests (por identificar) |
| INFRA-001 | Inventario/telemetría de VPS | Infraestructura | Chat infraestructura SaaS | PROPUESTO | Sin rama | Módulo de observabilidad (por definir) |
| INFRA-002 | Storage escalable y afinidad por Tenant | Infraestructura | Chat infraestructura SaaS | PROPUESTO | Sin rama | Almacenamiento, modelos, migraciones (por definir) |
| INFRA-003 | Backups y recuperación probada | Infraestructura | Chat infraestructura SaaS | PROPUESTO | Sin rama | Scripts y pruebas (por definir) |
| ITEMS-202-A | Reescaneo histórico XML, idempotencia y protección de documentos | Contabilidad de Ítems | Chat PR #208 | PR ABIERTO / EN PRUEBAS | `fix/issue-202-tenant-idempotency-20261015` / #208 | `backend/app/services/contabilidad_items_ubl.py`, `backend/app/services/contabilidad_items_reescaneo.py`, tests asociados |
| ETAPA-7 | Landing/CMS/planes/NEXUS comercial | Comercial | Chat Etapa 7 | RESERVADO A OTRO CHAT | Consultar sus PR | Website y comercial |

**Importante:** no se afirma que los PR abiertos no relacionados estén libres; inspeccionar GitHub antes de tocar archivos. Un cambio de estado requiere evidencia (commit, pruebas, PR o despliegue).

## Evidencia ITEMS-202-A (15/10/2026)

- Issue [#202](https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/issues/202), apartado A; [PR #208](https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/208) permanece en borrador, no fusionado ni desplegado.
- Implementado EN RAMA: lectura por cursor de páginas XML, validación de SHA-256 y ruta por tenant, registro parcial de ítems idempotente secuencial con savepoints.
- Workflows `backend`, `recepcion-documental-ci` y `roles-real-integration` aprobados para el commit `ff270eeb`; la rama requiere ponerse al día con main y repetir CI.
- Pendiente: endpoints con RBAC, trabajos asíncronos reanudables, checkpoints persistentes, concurrencia, auditoría, E2E, validación de restauración y revisión de colisiones con otras ramas.
- Coordinación: respetar Etapa 7, arquitectura SUPERADMIN/tenants e infraestructura; cualquier cambio en archivos compartidos se avisa previamente.
