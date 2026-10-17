# FACT CENTRAL — Gate de restauración antes de I / D (17-10-2026)

**No ejecutar fusion ni despliegue.** Revisión del commit combinado `78e31489069036c98951d21942fb09b899364c0e` en rama aislada `integration/208-main-review-20261017`.

## Evidencia de CI

Cinco workflows GitHub Actions terminaron **SUCCESS** en el SHA combinado:
- `backend` 39066933733
- `recepcion-documental-ci` 39066933753
- `roles-real-integration` 39066933755
- `items-migration-ci` 39066933769
- `coordination-guardrails` 39066933742

## Gate pendiente de backup/restore

**NO VERIFICADO:** restauración integral de PostgreSQL y los archivos/documentos del volumen `fact_central_documentos`. Los workflows automáticos anteriores no lo demuestran.

El workflow manual `.github/workflows/restore-check-vps-staging.yml` usa `workflow_dispatch`, lee un dump fijo `factcentral_20261014T042911Z.dump`, verifica SHA256 y crea/restaura/elimina una base temporal. Con `preflight_0034=false` **no** prueba archivos; la rama condicionada para archivos requiere `preflight_0034=true` y la rama especial `feature/separacion-cotizaciones-documentales-20261013`; no debe suponerse aplicable a esta release.

El script `deploy/preflight-backup-restore-items.sh` crea un dump fresco, verifica SHA256 y lo restaura en una base temporal, pero declara pendiente cotejar los documentos en el volumen, Alembic 0037 y pruebas completas. Su nombre no constituye evidencia de ejecución.

### Pasos para operador autorizado

1. Revisar `Actions > restore-check-vps-staging > Run workflow` y seleccionar conscientemente la rama. Antes de ejecutar comprobar que los secretos de **staging** apuntan exclusivamente al entorno autorizado y que el backup referenciado existe; `preflight_0034=false` solo valida BD, no archivos.
2. Guardar URL, run ID, SHA del workflow, fecha, conclusión y logs sin revelar secretos ni datos personales. Exigir `REST AURACION_VERIFICADA` (literal real `RESTAURACION_VERIFICADA`), comprobación del checksum, conteo y `BASE_ORIGINAL_INTACTA`. Si falla, detener integración.
3. Ejecutar **en staging, no en producción**, un ensayo adicional con respaldo de base y volumen de documentos: hash del archivo, extracción segura en un destino temporal, comparación de inventario y hashes de documentos seleccionados con sus registros de BD, lectura por tenant autorizado, restauración de expedientes, conteos de comprobantes, rutas y referencias. Anotar evidencias sin exponer información confidencial.
4. En una DB efímera restaurada, verificar `alembic_version`, upgrade 0039, downgrade 0039 y re-upgrade 0039, y checkpoint/idempotencia/rollback, sin tocar la DB original ni activar workers.
5. Confirmar limpieza de recursos temporales, backup utilizable, plan de retorno y aprobaciones de responsables.

**No hay acceso `workflow_dispatch` desde las herramientas actuales** ni logs aportados de restauración integral. El operador debe ejecutar la acción de GitHub en la interfaz y compartir la URL del run y su conclusión.

**Decisión actual:** no autorizar `I` hasta completar evidencia de archivos + base, revisión del PR #237 y aprobación explícita, ni `D` hasta preflight de despliegue independiente.
