# Auditoría documental de autodespliegue — Issue #235

Fecha: 2026-10-17  
Estado: **BLOQUEADO PARA CERTIFICACIÓN OPERATIVA**. Este documento no confirma ejecución remota ni modifica la VPS.

## Alcance revisado en main

- `.github/workflows/deploy-staging.yml`
- `deploy/preflight-secretaria.sh`
- `deploy/preflight-backup-restore-items.sh`
- `deploy/bootstrap-main.sh`
- `deploy/deploy.sh`
- PR #248 (`docs/protocolo-comandos-ia-20261017`)

## Hallazgos verificados en código

1. **Disparo por merge:** `deploy-staging.yml` contiene `push.branches: [main]`. Una fusión incluso documental puede disparar verificación y despliegue a `staging` si supera las condiciones configuradas. Bloquear PR #248 hasta resolver autorización del efecto real.
2. **Pruebas previas:** el job `deploy` depende de `verify-backend` y `verify-frontend`, y usa entorno `staging`; no se ha verificado la política real de aprobadores, secretos o branch protection desde la API disponible.
3. **Respaldo/restauración:** `preflight-backup-restore-items.sh` genera dump personalizado, valida hash SHA256 y restaura en base temporal con `pg_restore --exit-on-error`. El propio script avisa que siguen pendientes cotejo temporal de documentos en volumen, migración 0037 y downgrade/reupgrade aislado. Verificar que esos ensayos sean pertinentes y seguros antes de marcarlos como obligatorios.
4. **Preflight:** `preflight-secretaria.sh` comprueba cambios locales, colisiones, espacio, archivo de entorno, salud local y Docker; declara expresamente que NO certifica respaldo ni restauración.
5. **Versión:** `bootstrap-main.sh` exige el commit de destino y su ancestralidad, y lo compara con `origin/main`. Rechaza cambios versionados. `deploy.sh` comprueba el `EXPECTED_COMMIT` después de sincronizar.
6. **Comprobación posterior:** `deploy.sh` espera `/health`; esta señal no certifica por sí sola las rutas públicas `/`, `/ingresar`, `/bienvenida`, `/privacidad`, `/terminos`, ni integridad funcional o ausencia de regresiones.
7. **Sin rollback automático demostrado:** tras una falla del build o healthcheck, el script devuelve error y emite logs, pero no se observó reversión automática hacia el commit anterior. Antes de desplegar, exigir plan de recuperación verificado; no modificar despliegue en producción basándose solo en auditoría textual.

## Evidencia operativa indispensable (aún NO comprobada)

- Confirmar mediante interfaz de GitHub o API autorizada: reglas efectivas de branch protection/rulesets, revisiones obligatorias y permisos del environment `staging`.
- Identificar último SHA de `main`, ejecución de `deploy-staging` para ese SHA y estado verde de `verify-backend`, `verify-frontend` y `deploy`. Una consulta de runs de PR sin resultados **no demuestra** ausencia de despliegue por push.
- Obtener evidencias censuradas del preflight, respaldo fresco y restauración aislada (SHA256 verificado, conteos/versión Alembic). No copiar dumps, secretos ni datos sensibles al repositorio.
- Comprobar por canal autorizado el `git rev-parse HEAD` de VPS, servicios Docker, `/health` y rutas públicas requeridas; contrastar con SHA desplegado.
- Confirmar política de aprobación separada entre `I` (fusión) y `D` (despliegue) dado el disparo automático a través de `main`. No desactivar controles para permitir la fusión.
- Validar procedimiento de recuperación y riesgo de migraciones sobre datos reales sin ejecutarlas durante esta auditoría.

## Decisión

**No fusionar PR #248 ni modificar `main` o VPS desde la auditoría.** No cerrar Issue #235 sin evidencia operativa de los criterios anteriores. Mantener acciones de código potencialmente disruptivas en PR separado, con pruebas automatizadas y verificación de entorno aislado.

## Siguiente fase recomendada

`S` para reunir evidencia faltante de GitHub Actions/environments y VPS, sin fusionar ni desplegar. Si no existe acceso operativo para obtenerla, emitir bloqueo concreto y entregar instrucciones mínimas de comprobación al operador autorizado.
