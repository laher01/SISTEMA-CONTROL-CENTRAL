# Estado exacto del motor de recuperación — PR #264

**No ejecutar en VPS ni fusionar.**

## Implementado
- Auditor offline de manifiesto pareado, SHA256 y validación segura de rutas y tipos TAR.
- Preflight offline de separación de orígenes/destinos, confirmación, bases distintas y volumen temporal vacío.
- Evaluador offline de correspondencia entre referencias sintéticas documento/expediente por tenant, rechazo de huérfanos, faltantes y referencias cruzadas.
- Verificador **sintético** de secuencia 0038→0039→0038→0039 y política RBAC por tenant, con tests automatizados.
- Entrada `workflow_dispatch` que sólo verifica controles locales, deliberadamente sin SSH ni ejecución de restauraciones.

## NO implementado ni ejecutado
- Snapshot consistente remoto de base PostgreSQL + volumen documental.
- `pg_restore` real a base efímera ni restauración/rehidratación real de documentos.
- Consultas a esquema real para vincular `documentos`, `expedientes` y paths de almacenamiento, ni control de hashes de producción.
- Autenticación real de dos cuentas sintéticas contra el backend restaurado.
- Ejecución de Alembic 0039 y rollback con conexión a PostgreSQL recuperado.
- Limpieza transaccional verificable y rollback de infraestructura tras fallos.

Estas operaciones requieren infraestructura staging aislada, esquema de storage confirmado, permisos mínimos revisados, workflow separado aprobado y supervisión humana. El CI de pruebas sintéticas no habilita por sí solo producción.

**Gate S abierto. No aprobar I/D.**
