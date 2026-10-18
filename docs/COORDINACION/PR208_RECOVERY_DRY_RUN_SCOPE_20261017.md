# Gate S — alcance del workflow experimental

**NO APROBADO PARA RECUPERACIÓN REAL.** Este PR añade exclusivamente un validador local de un par de backups y un workflow manual/PR de **pruebas sintéticas sin SSH**. No se conecta a staging, no toma snapshots, no restaura PostgreSQL ni comprueba RBAC sobre una base real.

- `deploy/recovery_pair_audit.py`: requiere un mismo batch y SHA256 para dump PostgreSQL y tar.gz documental; inspecciona las rutas del archivo sin extraerlo y rechaza archivos que no sean regulares, symlinks/hardlinks, rutas absolutas, ascensos y duplicados; valida manifiesto individual de tamaño y SHA256.
- `deploy/test_recovery_pair_audit.py`: pruebas con archivos sintéticos (recuperación de manifiestos correctos y rechazo de casos peligrosos).
- `.github/workflows/security-paired-restore-dry-run.yml`: workflow manual confirmando `OFFLINE-ONLY` y CI por PR, sin secretos, SSH ni rutas de despliegue.

## Límites pendientes antes de levantar S
1. Revisar el workflow y pruebas offline; no ejecutarlo como sustituto del ensayo real.
2. Operador autorizado verifica aislamiento staging-productivo, prepara snapshots realmente coordinados con identificador de lote y manifiesto, y provee ubicaciones de copias temporales con hashes.
3. En un entorno de restauración separado, con herramientas aprobadas y bajo supervisión, restaurar `pg_restore` en base efímera y documentos en directorio efímero seguro; comprobar la correspondencia de rutas de `documentos`, expedientes, permisos RBAC y tenant.
4. Ejecutar Alembic 0039 / downgrade / reupgrade **exclusivamente en copia**; registrar SHA, logs y limpieza.
5. Comparar el número de registros de respaldo contra la **misma** instantánea, investigar 2305 vs 687 (histórica); no asumir igualdad con lecturas recientes.
6. Revisión de seguridad del tar: imponer límites de tamaño/descompresión y políticas de symlinks y evitar extraer archivos arbitrarios sin revisión adicional.

**No existe aún workflow de recuperación coordinada remota**, ni resultados de recuperación real de este PR. No fusionar ni desplegar. Mantener S abierto.
