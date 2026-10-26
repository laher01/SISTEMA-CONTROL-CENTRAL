# Oracle: recuperación y activación segura del autodespliegue

## Alcance
Servidor autorizado `132.145.233.172`, aplicación pública `https://app.nexomarnegocioseirl.online/`. No utilizar otros dominios. No se ha modificado Oracle.

## Controles de activación por separado
- En `push` a `main`, desplegar requiere **dos condiciones independientes**: variable de repositorio `ORACLE_AUTO_DEPLOY_ENABLED=true` y variable del entorno **`oracle-autodeploy`** `ORACLE_RECOVERY_VERIFIED=true`.
- En PR el job `deploy` debe estar omitido.
- Manual usa environment `staging`; automático usa `oracle-autodeploy`. Los secretos SSH se deben provisionar *por separado*, sin copiarlos a archivos del repositorio.
- El entorno nuevo debe restringir ramas de despliegue a `main`. Revisar quién puede actualizar sus secrets y variables. La eliminación de `Required reviewers` de `staging` **no está recomendada**.

## Respaldo y restauración
La ejecución validada de `deploy/preflight-backup-restore-items.sh` prepara volcado PostgreSQL, verifica SHA256, crea DB temporal aislada, restaura, comprueba documentos/Alembic y elimina solamente la DB temporal. `bootstrap-main.sh` y `deploy.sh` generan respaldos adicionales y verifican SHAs. No confundir recuperación probada de la base con recuperación completa de aplicación y archivos PDF.

## Bloqueante de recuperación completa
Actualmente `deploy.sh` no restaura automáticamente una versión anterior de contenedores después de fallar `/health`. Tampoco se comprueba automáticamente compatibilidad reversible de migraciones ni recuperación del volumen documental. **No declarar listo el autodespliegue ni poner `ORACLE_RECOVERY_VERIFIED=true`** hasta demostrar en entorno aislado:
1. Registro del SHA anterior y de la versión de imagen previa.
2. Recuperación reproducible del código, contenedores, base PostgreSQL y volumen documental, con verificación de integridad.
3. Procedimiento seguro ante migraciones no reversibles, que bloquee rollback automático incompatible.
4. Pruebas de fallo simulado y recuperación con RTO/RPO acordados; validación de rutas críticas OCR/PDF, autenticación y segregación de tenants.
5. Prueba pública no destructiva contra `app.nexomarnegocioseirl.online`, y política de detener nuevos despliegues tras un fallo.

Si falla un despliegue sin estas garantías, dejar automatización desactivada y ejecutar recuperación **solo con autorización y respaldo comprobado**; no ejecutar rollback ciego de base de datos.

## Configuración administrativa todavía pendiente
GitHub → Settings → Environments: crear `oracle-autodeploy`, definir ramas permitidas `main`, configurar los cinco secretos usados en staging (sin compartir valores), comprobar políticas de autorización y separar permisos respecto a otros workflows. GitHub → Settings → Secrets and variables → Actions: NO activar `ORACLE_AUTO_DEPLOY_ENABLED` todavía.
Protecciones efectivas de `main`, revisores y CI obligatorios deben verificarse administrativamente antes de iniciar despliegues automáticos.

## Activación
Activar las variables **solamente mediante autorización específica posterior a pruebas de recuperación**. La creación e integración del PR no autoriza activación ni despliegue.
