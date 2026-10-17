# Preintegración PR #208 — revisión aislada (17-10-2026)

Estado: **BLOQUEADO PARA INTEGRAR / DESPLEGAR**. Esta rama se creó desde `main`; NO contiene una fusión de #208 y no altera ninguna rama operativa.

## Evidencias comprobadas
- PR #208, SHA `bf24bedb7f2fc3f4542ba4fc2f39afbad84cf119`: **4/4 workflows SUCCESS** (backend, recepción, roles, migración); continúa DRAFT.
- Comparación en GitHub: **67 commits ahead / 40 behind** de `main`. La herramienta usada permite comparar y crear ramas, pero no aplicar una fusión local de dos historias ni resolver conflictos. Este paso permanece **PENDIENTE**, no se presenta como terminado.
- PR #237, SHA `0e1aa4528fb3a3dce66180f60752a4d5be5a2570`: **5/5 CI SUCCESS**; revisión resuelta. Mantenerlo separado hasta comprobar solapamientos.
- PR #249: revisión antitraversal redundante con controles que ya están presentes en #208; no duplicar.
- Migración `0039` de trabajos XML usa `down_revision=0038`, y `0038` está presente en `main`. `items-migration-ci` valida upgrade/downgrade/reupgrade con PostgreSQL sintético; no equivale a compatibilidad de todas las ramas ni restauración productiva.
- Archivo `deploy/preflight-backup-restore-items.sh` contiene backup fresco, SHA256, restauración en BD temporal y cleanup. **No se ha ejecutado contra la VPS desde esta revisión.** El script advierte que queda cotejar el volumen documental y migración 0037 en BD aislada.
- `restore-check-vps-staging.yml` usa SSH y un respaldo de fecha fija; no se ejecutó ni sustituye ensayo integral de este release.

## Secuencia para levantar el bloqueo
1. Acordar responsable y ventana de integración; verificar que no existan cambios concurrentes en archivos compartidos.
2. En esta rama aislada, integrar **sin force-push** los commits de #208 mediante herramienta Git que cree merge ordinario (no sobrescribir `main`); resolver conflictos preservando las mejoras de NEXUS, frontend, seguridad y coordinación. Registrar SHA resultante y diff.
3. Ejecutar CI en el **SHA conciliado**: backend completo, RBAC, multitenant, reintentos, idempotencia concurrente PostgreSQL, migración y frontend; revisar con #237 y #249. No dar por verde un SHA anterior.
4. Ensayar backup/restauración **aislada** con datos y documentos: verificar integridad, hash, expedientes, contadores, alembic_version, upgrade/downgrade de 0039, tiempos y plan de retorno. No usar producción como base de pruebas.
5. Verificar que no existen worker/POST de ejecución masiva activos y revisar límites/permisos de las rutas.
6. Sólo tras nueva evidencia y aprobación explícita para `I` considerar merge; `D` requiere una orden posterior y su propio preflight, respaldo, healthchecks y reversión.

Ninguna operación `I` ni `D` se ejecutó en este análisis.

## Inspección adicional de conciliación (17/10)
- Comparación de archivos cambiados desde las dos perspectivas: 13 rutas modificadas por #208 frente a 27 por main; **intersección de rutas: 0**. No demuestra ausencia de conflictos semánticos ni equivalencia de build.
- Se identificaron herramientas GitHub para crear árboles y commits multipadre, pero no acceso de lectura verificado a árboles completos de commits; no se construyó un árbol de fusión a ciegas. No existe commit de conciliación ni CI sobre uno nuevo.
- El checkout aislado continúa anclado a main con este informe. Para conciliar, usar un Git real en entorno autorizado con `git merge --no-ff` sobre rama aislada, inspeccionar estado y ejecutar CI. **Nunca apuntar main al resultado sin aprobación I explícita.**
- Validación real de respaldo y restauración de datos/documentos: no ejecutada; se revisaron workflows y script preflight, pero eso solo acredita existencia de mecanismos, no resultado de recuperación.
