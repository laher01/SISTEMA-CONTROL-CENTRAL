# FACT CENTRAL — Guía de coordinación para asistentes

Antes de modificar código, leer [docs/COORDINACION/00_LEER_PRIMERO.md](docs/COORDINACION/00_LEER_PRIMERO.md).

- Fuente de verdad: `main` y PR/Issues del repositorio `laher01/SISTEMA-CONTROL-CENTRAL`.
- SaaS multi-tenant; prohibido cruzar datos entre tenants. SUPERADMIN solo lectura operativa autorizada.
- Revisar trabajos activos, archivos compartidos y responsable asignado antes de editar.
- No fusionar ni desplegar sin autorización expresa del usuario.
- No publicar secretos. Registrar pruebas, impacto, pendientes y estado real.
- Si aparece un trabajo concurrente del Centro de Coordinación, detener el PR duplicado y conciliar.
