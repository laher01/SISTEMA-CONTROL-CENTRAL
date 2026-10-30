# Trabajos en curso y reserva de áreas

**Verificar antes de usar:** este archivo no reemplaza Issues, PR y ramas recientes.

| ID | Trabajo | Área | Responsable | Estado | Rama / PR | Archivos previstos |
| --- | --- | --- | --- | --- | --- | --- |
| COORD-001 | Crear Centro de Coordinación | Coordinación | Chat arquitectura SaaS | PR EN PREPARACIÓN | `docs/centro-coordinacion-saas-20261015` | `AGENTS.md`, `docs/COORDINACION/**` |
| SAAS-001 | Consola SUPERADMIN consulta integral solo lectura | SaaS | Chat arquitectura SaaS | PROPUESTO | Sin rama | Backend/frontend SUPERADMIN (por identificar) |
| SAAS-002 | Auditoría de aislamiento cross-tenant | Seguridad | Chat arquitectura SaaS | PROPUESTO | Sin rama | Servicios API, autenticación, tests (por identificar) |
| INFRA-001 | Inventario/telemetría de VPS | Infraestructura | Chat infraestructura SaaS | PROPUESTO | Sin rama | Módulo de observabilidad (por definir) |
| INFRA-002 | Storage escalable y afinidad por Tenant | Infraestructura | Chat infraestructura SaaS | PROPUESTO | Sin rama | Almacenamiento, modelos, migraciones (por definir) |
| INFRA-003 | Backups y recuperación probada | Infraestructura | Chat infraestructura SaaS | PROPUESTO | Sin rama | Scripts y pruebas (por definir) |
| OCR-MISD-001 | Unir ingreso fiscal OCR y correcciones MISD sobre main 703d20c4 | Documentos / MISD | Continuación autorizada por usuario | EN VALIDACIÓN; sin integrar | `fix/misd-ocr-joint-703d20c4` / PR borrador por crear | Rutas MISD, permisos, solicitudes, tests y los 3 archivos de PR #405 |
| EXP-ORQ-001 | Purgar expediente al retirar su último documento, evitar reutilizar cascarones, ocultar carga no Gestor y previsualizar vacíos | Expedientes / RBAC | Orquestador de Desarrollo — Sistema Control Central | INTEGRADO EN `main`; staging workflow exitoso | PR #421 / SHA `854e3952` | Rutas de expedientes/documentos, servicios de ingesta, detalle de expediente y pruebas de regresión |
| ORQ-PAG-001 | Añadir números clicables basados en conteos reales a Documentos, Expedientes y Registros, conservando filtros | UX compartida / Listados | Orquestador de Desarrollo — Sistema Control Central | INTEGRADO EN `main`; commit `c8ed2ad0` | PR #422 | `frontend/src/componentes.tsx`, listados documentales, estilos y pruebas |
| EXP-ORQ-002 | Excluir expedientes sin documentos activos de consultas y totales por rol; depurar históricos vacíos tras previsualización segura | Expedientes / Dashboard / Finanzas | Orquestador de Desarrollo — Sistema Control Central | INTEGRADO EN `main` PR #423; despliegue bloqueado por error de fixture PostgreSQL | `fix/expedientes-vacios-por-rol-20261030` / SHA `456db137` | Rutas de expedientes, dashboard, alertas y módulos financieros; servicio de limpieza y regresiones |
| COB-ORQ-001 | Hacer visibles en Cobros los expedientes activos excluidos por receptor no autorizado o sin vínculo a Gerencia/Pedido | Cobros / Comisiones | Orquestador de Desarrollo — Sistema Control Central | EN VALIDACIÓN LOCAL; PR pendiente | `fix/cobros-resumen-atribucion-20261030` | `backend/app/api/routes/pagos_responsables.py`, pruebas de cobros, `frontend/src/paginas/MiEquipoResponsable.tsx` |
| ETAPA-7 | Landing/CMS/planes/NEXUS comercial | Comercial | Chat Etapa 7 | RESERVADO A OTRO CHAT | Consultar sus PR | Website y comercial |

**Importante:** no se afirma que los PR abiertos no relacionados estén libres; inspeccionar GitHub antes de tocar archivos. Un cambio de estado requiere evidencia (commit, pruebas, PR o despliegue).
