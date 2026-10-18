# PR 264 — Auditoría de cobertura y gate S (17/10/2026)

## Verificación de CI
Commit `afb0296dab2e3245d2888bad7d3b1cc34653e8b3`: **7 de 7 workflows SUCCESS**, incluyendo backend, recepcion-documental-ci, roles-real-integration y cuatro controles de seguridad. La ejecución `security-synthetic-postgres-restore-ci` 39084126363 muestra `RESTORED_SYNTHETIC_STORAGE_REFERENCES_OK: 2`, `ALEMBIC_0039_REAL_ROUNDTRIP_OK`, `RESTORED_FASTAPI_AUTHENTICATION_AND_RBAC_OK` e `INTERRUPTION_CLEANUP_VERIFIED`.

## Comparación de workflows
| Prueba | security-postgres-ephemeral-restore-ci | security-synthetic-postgres-restore-ci |
| --- | --- | --- |
| PostgreSQL | 17 | 16 |
| pg_dump/pg_restore | sí, docker postgres:17 | sí, cliente instalado en runner |
| Alembic 0038/0039 downgrade/reupgrade | sí | sí |
| Preservación de marcador relacional | sí | sí, tablas reales con fixtures |
| Archivos TAR, manifiesto SHA256 individual | pruebas de auditor en paso aparte | prueba completa de recuperación documental |
| Comprobación documento–expediente–tenant | no | sí |
| FastAPI RBAC contra DB restaurada | no | sí |
| Limpieza después de fallo inducido | trap básico | probada con inyección de fallo |

**Decisión de consolidación:** NO ELIMINAR workflow de PostgreSQL 17 aún. El workflow de PostgreSQL 16 no prueba equivalencia de versión 17. Para consolidar, ejecutar las pruebas completas en una matriz PostgreSQL 16/17 con clientes compatibles antes de eliminar el antiguo; evitar regresión de portabilidad.

## Criterios todavía pendientes
1. Restauración pareada real en staging separado de producción con backups coordinados y evidencias de integridad.
2. Validación sobre esquema real y documentos de staging de tenants/expedientes, sin revelar contenido privado en logs.
3. Revisión de seguridad del flujo remoto, aprobación independiente, plan de rollback, limpieza ante interrupciones de proceso/runner (no solo fallo controlado).
4. Comprender los conteos históricos 2305 (backup) / 687 (origen) y la incompatibilidad temporal con el respaldo documental de 654 archivos.
5. Confirmar inequívocamente destino staging y permisos de ejecución antes de operación alguna.

S ABIERTA; I y D bloqueados. Ningún despliegue, fusión o acceso VPS.
