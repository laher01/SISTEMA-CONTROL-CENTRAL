# PR #264 — Auditoría de rollback adversarial y gate S (17/10/2026)

## Cobertura confirmada
En commit base `f33058798d78b8ea2847e9c06cf315748c849b2c`, el ensayo de restauración PostgreSQL 16/17, coordinación y pruebas offline estaban SUCCESS. Las otras verificaciones generales aún aparecían en ejecución al inicio de esta iteración.

## Corrección puntual
- `deploy/recovery_safe_extract.py`: durante el rollback de directorios se usa `_open_directory(..., create=False)` para evitar que la limpieza cree una ruta eliminada concurrentemente. Antes se había aplicado solo al rollback de archivos.
- `deploy/test_recovery_safe_extract.py`: pruebas de ausencia de recreación de padre, conservación de archivo preexistente y rechazo de destino no vacío.
- Estos tests no prueban todas las carreras entre procesos: una sustitución simultánea de inodos puede exceder las protecciones actuales, por lo que staging necesita un directorio desechable exclusivo, aislamiento de UID y montaje, control de cuotas e inspección posterior.

## Limpiador sintético
`deploy/recovery_orphan_cleanup.py` conserva `dry-run` por defecto, no toca bases de datos y no elimina recursos con marcador PID. No habilitar su opción `--apply` fuera de un entorno CI desechable, propiedad exclusiva y sin escritores concurrentes: los marcadores JSON no son identidades criptográficamente autenticadas.

## Criterio para S
Solo podrá cerrarse tras ensayos pareados de almacenamiento+PostgreSQL en staging genuinamente aislado, evidencias de integridad documental y relaciones multitenant, RBAC sobre copia restaurada, rollback ante fallos, reconciliación después de terminación abrupta y aprobación humana independiente.

**S abierta, I y D bloqueadas; PR #264 draft, sin VPS/merge/deploy.**
