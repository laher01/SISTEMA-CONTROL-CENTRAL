# Evidencia y límites — ensayo Docker de recuperación del PR #394

## Diseño reproducible
Workflow `.github/workflows/deploy-staging.yml` → job `verify-recovery-docker` ejecuta `tests/integration/recovery_docker_isolated.sh` en un runner desechable Ubuntu con Docker.
- PostgreSQL 17 en contenedor temporal con un volumen Docker propio.
- Dos documentos sintéticos de tenants `alpha` y `beta` en un segundo volumen desechable.
- Backup PostgreSQL formato custom y TAR documental con sumas SHA256.
- Simulación de pérdida (TRUNCATE de **datos sintéticos** y borrado de **archivos sintéticos**).
- Restauración en BD temporal `recovered`, restauración documental, verificación de filas/archivos.
- Recreación del contenedor de PostgreSQL y confirmación de persistencia.
- `trap` elimina contenedor, volúmenes y archivos temporales, incluso ante fallos.
- CI exige que este job y las pruebas anteriores finalicen satisfactoriamente antes de considerar `deploy`.

## Límites de lo demostrado
Los tenants son fixtures de base de datos, no una verificación de autorización RBAC de la aplicación. La prueba no ejecuta migraciones de Alembic de FACT CENTRAL, ni reconstruye el backend y frontend reales, ni prueba el flujo OCR/PDF con usuarios. Tampoco demuestra recuperación de todos los volúmenes, secretos o migraciones de producción.

**Esta prueba no habilita `ORACLE_RECOVERY_VERIFIED`.** Para certificar recuperación completa se requiere un ensayo aislado de la aplicación real y datos/volúmenes de prueba equivalentes, incluyendo Alembic, compatibilidad de migraciones, tenants y OCR/PDF.

## Infraestructura y seguridad
No utiliza VPS Oracle, producción ni credenciales SSH. `oracle-autodeploy` permanece sin certificar administrativamente; no modificar variables ni ambientes por este test.

## Evidencia
Consultar la última ejecución del workflow del SHA del PR, job `verify-recovery-docker`. Una prueba solo puede calificarse como aprobada tras que Actions publique `success`; nunca inferirlo de la existencia del script.
