# Oracle — despliegue automático controlado (propuesta)

## Alcance
- VPS autorizada: `ubuntu@132.145.233.172`, checkout `/home/ubuntu/fact-central`.
- Destino público de la aplicación: `https://app.nexomarnegocioseirl.online/`.
- No realizar pruebas ni monitorización usando el dominio de otra VPS.
- Los secretos SSH manuales permanecen en `staging`; los del despliegue automático deben provisionarse en el environment separado `oracle-autodeploy`, nunca en el repositorio.

## Regla de activación
La nueva ruta automática se ejecuta solo tras un `push` a `main` **y** si la variable GitHub Actions `ORACLE_AUTO_DEPLOY_ENABLED` tiene el valor exacto `true`.
El valor ausente, vacío o distinto de `true` **bloquea automáticamente el job de despliegue**. Además, el entorno exclusivo `oracle-autodeploy` exige `ORACLE_RECOVERY_VERIFIED=true` para ejecutar un push automático; no debe establecerse sin recuperación integral probada. El disparo manual desde `main` sigue disponible. La fusión del PR, por sí sola, **no activa** el despliegue automático.

## Verificaciones integradas antes de desplegar
- CI backend: Ruff, mypy y pytest con PostgreSQL temporal.
- CI frontend: lint, tipos, pruebas y build.
- La etapa `deploy` requiere éxito de ambos jobs.
- Se verifica que el evento es admisible, rama `main` y autorización de variable.
- Se comprueba host, usuario, ruta y secretos SSH.
- Se ejecuta la verificación previa; a continuación, respaldo y restauración aislada mediante `deploy/preflight-backup-restore-items.sh`.
- El bootstrap existente valida SHA, aplica controles y despliega la versión objetivo solo si los pasos anteriores superan las verificaciones.
- Comprobaciones posteriores existentes del despliegue: contenedores y salud local; antes de certificar salida pública es necesaria prueba HTTPS sobre el subdominio de NEXOMAR.

## Ajuste manual pendiente (GitHub → Settings → Environments → staging)
1. Antes de activar, verificar en `staging` los **Required reviewers** y **Deployment branches and tags**; no asumir que están activados ni modificar revisores sin autorización.
2. Para que el despliegue se ejecute sin aprobación por cada push, el administrador deberá revisar **Required reviewers** exclusivamente en el nuevo environment `oracle-autodeploy`, **solo tras revisar los riesgos**. Si otros workflows sensibles comparten `staging`, mejor crear un environment exclusivo de despliegue y migrar secretos/control de acceso con aprobación independiente.
3. Mantener restricción para desplegar únicamente desde `main`, políticas de revisión de PR y controles de CI. Conservar los permisos de administrador de `laher01`.
4. Una vez aprobados CI, recuperación y protecciones administrativas, configurar variable de repositorio `ORACLE_AUTO_DEPLOY_ENABLED=true` en **Settings → Secrets and variables → Actions → Variables**. Esta es una acción de activación **separada**, NO autorizada por el PR.
5. Antes de activar la variable, confirmar que la fusión de este workflow no introduce una ejecución inesperada sobre Oracle. No habilitar el valor `true` en la misma operación de integración.

## Riesgos y límites
- Cada push a `main` tras la activación podría actualizar Oracle; impedir pushes sin revisión y exigir reglas de protección.
- Cambios solo de documentación también iniciarían CI y podrían desplegar el mismo SHA; evaluar filtros de rutas antes de operar de forma permanente.
- `staging` podría albergar otros workflows con acceso SSH: quitar revisores de ese environment afectaría también a estos, por lo que se debe evaluar separar environments.
- No se modifican fórmulas económicas, expedientes, datos fiscales ni permisos de usuarios.
- El PR no fusiona ni despliega.
