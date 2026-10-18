# Gate S — Verificación de capacidad remota, VPS antigua staging (18-10-2026)

## Resultado de esta ejecución
- Prioridad: **VPS antigua staging**, no VPS Oracle.
- `main:.github/workflows/alembic-vps-diagnostic.yml` consultado. Tiene `workflow_dispatch`, `permissions: contents: read`, `inspect-staging` únicamente si evento manual y rama `refs/heads/main`, con `environment: staging` y SSH a host permitido `132.145.233.172` usuario `ubuntu`.
- `main:deploy/inspect-alembic-readonly.sh` consultado. Comprueba existencia no vacía de `deploy/.env.production` sin imprimirlo; consulta `git rev-parse HEAD`, realiza `SELECT version_num FROM alembic_version ORDER BY version_num` con psql vía `docker compose exec -T db`, y verifica presencia de `pg_restore` sin restaurar.
- **No ejecutado**: workflow_dispatch, SSH, comandos VPS, migraciones, Docker up/down, restauraciones ni despliegue.
- Motivo: el conector GitHub expuesto en este chat no proporciona acción `workflow_dispatch` ni SSH directo; acciones de consulta y reejecución de jobs no son equivalentes a iniciar diagnóstico manual. La mera configuración de secretos no acredita credenciales vigentes ni conectividad.
- La inspección de código confirma intención de operaciones de lectura; no verifica los efectos del contenedor en ejecución ni el estado actual de VPS.
- CI último conocido de PR #296 SHA `a461c1d3468c3bcbf592e93a307c1feea4587f5b`: coordination-guardrails SUCCESS; no hay CI backend ni prueba remota para ese SHA.

## Método autorizado para levantar el bloqueo (manual, no ejecutado)
Un operador con permisos en GitHub debe abrir `Actions > alembic-vps-diagnostic > Run workflow` en `main`, comprobar que el environment staging es el pretendido y autorizar la ejecución. Revisar logs del job `inspect-staging` y retener únicamente commit, versión Alembic, conclusión SSH y metadatos no sensibles. No reenviar secretos o contenido .env.

## Evidencia requerida para cerrar este subgate
Workflow run ID, SHA de main del evento, conclusión del job validate-script, conclusión inspect-staging, commit VPS y versión Alembic obtenidos. Si falla, registrar únicamente categoría (environment/secrets/destino SSH/docker/DB), sin exponer secretos.

## Restricciones
Gate S OPEN. PR #264/#290/#293/#294/#296 DRAFT. No modificar main, VPS, secrets, migraciones ni desplegar. Oracle no incluido en este diagnóstico.
