# Despliegue independiente del PR #140 a VPS antigua

**Autorización de destino:** VPS antigua exclusivamente `ubuntu@132.145.233.172`.
**Código aprobado:** `0565b97469c1a6bb2e0e6f35de3d2f8949696299` (`integration/document-capture-main-20261011`).
**Prohibiciones:** no fusionar `main`, no actualizar Oracle, no ejecutar `deploy/deploy.sh` sin revisión porque dicho script hace `git pull --ff-only origin main`.
**Estado:** instrucción de operación, NO certificado de instalación.

## Condiciones obligatorias antes de tocar producción
1. Confirmar acceso SSH administrado a la VPS antigua y sus secretos de entorno `staging`. No introducir secretos en Git ni registros públicos.
2. Confirmar hostname/IP real del servidor y que NO es Oracle; ejecutar `hostname -f`, `ip addr`, `git remote -v` y `git status --porcelain` solo de lectura.
3. Verificar Docker/Compose, espacio libre, RAM, healthcheck actual (`curl -fsS http://127.0.0.1:18080/health`), estado DB y su plan de restauración.
4. Hacer un backup PostgreSQL de formato custom y **verificarlo con `pg_restore --list`** sin exponer datos. Guardar respaldo fuera de la ruta de trabajo antes de modificar servicios.
5. Suspender cualquier actualizador local en la VPS antigua que pueda pisar el código con `origin/main`; documentar su estado y restaurarlo solo tras definir política de actualización independiente.
6. Aislar la revisión de las otras ramas: no incorporar PR ajenos, no resetear cambios locales, no resolver conflictos sobrescribiendo archivos.
7. Antes de construir, comparar SHA remota y versión exacta aprobada. Evitar `git pull main` como parte de esta entrega; despliegue de commit fijado e identificado. Un operador debe adaptar el procedimiento porque `deploy/deploy.sh` actual obliga a desplegar `main`.
8. En ejecución aprobada, confirmar backup, build de la versión fijada, despliegue controlado y healthcheck; comprobar funcionalidad de cámara, carga múltiple, OCR, reprocesamiento forzado, aislamiento tenant y jerarquías.
9. Ante fallo de healthcheck, detener la promoción. No suponer que revertir contenedores revierte migraciones. Recuperar solo mediante runbook comprobado y respaldos consistentes.
10. Registrar hora, commit, resultado CI, identidad del servidor, copia de seguridad, estado posterior y evidencias operativas, sin secretos.

## Verificaciones registradas en GitHub
Para el commit `0565b97469c1a6bb2e0e6f35de3d2f8949696299`: cinco workflows de PR concluyeron con success (backend, frontend, recepcion-documental-ci, roles-real-integration, roles-browser-isolated).

## Nota operacional crítica
El flujo `.github/workflows/deploy-staging.yml` desplegaría automáticamente `main`, no necesariamente la versión de este PR. El actualizador de Oracle también sigue `origin/main`. Por lo tanto, **no fusionar el PR #140 para intentar instalar esta versión**. La instalación independiente solo debe ejecutarse con un canal operacional real verificado en la VPS antigua.
