# Despliegues y pendientes de verificación

**Este documento no implica acceso en vivo a la VPS.**

- Despliegue staging: revisar `.github/workflows/deploy-staging.yml`, `deploy/preflight-secretaria.sh`, `deploy/bootstrap-main.sh` y `deploy/deploy.sh` antes de ejecutarlo.
- El flujo está diseñado para autorización manual, verificación de secretos, respaldo PostgreSQL, reconstrucción, migraciones y healthcheck; la ejecución final no está verificada aquí.
- No registrar "DESPLEGADO" por el mero hecho de fusionar un PR.
- No almacenar IP/usuarios/contraseñas/llaves SSH en registros de coordinación cuando no sean necesarios; nunca registrar claves.
- Antes de implantar storage distribuido, auditar metadatos, escritura/lectura, aislamiento de Tenants, backups y rehidratación.
- Antes de implantar failover, probar restauración de datos y documentos en entorno aislado y fijar objetivos RTO/RPO.

| Requisito | Estado |
| --- | --- |
| Consola SUPERADMIN lectura integral auditada | PENDIENTE DE IMPLEMENTAR/VERIFICAR |
| Inventario y monitoreo de nodos VPS | PENDIENTE |
| Storage distribuido por Tenant | PENDIENTE |
| Backups independientes y restauración probada | PENDIENTE |
| Despliegue y validación remota de estos módulos | NO REALIZADO |
