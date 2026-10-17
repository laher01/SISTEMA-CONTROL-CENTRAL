# Gate S — restauración conjunta Fact Central / NEXUS 2.0

Fecha de revisión: 2026-10-17. Commit integrado ensayado: `78e31489069036c98951d21942fb09b899364c0e` (5/5 CI SUCCESS).

**Estado: PENDIENTE DE EJECUCIÓN Y EVIDENCIA.** No se lanzó ningún workflow, ni se restauró ningún recurso del servidor desde esta revisión. Nada aquí autoriza I ni D.

## Dos pruebas manuales disponibles en GitHub Actions

1. [restore-check-vps-staging](https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/actions/workflows/restore-check-vps-staging.yml). Restauración aislada de PostgreSQL mediante backup fijo `factcentral_20261014T042911Z.dump`, SHA256, DB temporal, recuentos y limpieza. En rama `main` con `preflight_0034=false` no valida archivos. `preflight_0034=true` depende de rama de trabajo histórica distinta: **no sustituye validación 0039**.
2. [restore-check-documents-vps-staging](https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/actions/workflows/restore-check-documents-vps-staging.yml). Verifica SHA256 de `documentos_20261010T054030Z.tar.gz`, extracción en `/tmp`, conteo de archivos y limpieza del directorio temporal; **no comprueba hashes de cada archivo ni correspondencia documental en base restaurada**.

**Riesgo de desfase:** los respaldos citados son de fechas diferentes (10 y 14 de octubre); no deben declararse un par consistente ni usarse para afirmar restauración integral. Antes de test de consistencia se requiere snapshot coordinado y fresco de base+volumen.

## Operación autorizada y evidencias exigidas

- Operador con acceso GitHub Actions y environment `staging`: validar que destino y secretos corresponden al entorno permitido y que no se está ejecutando en el servicio productivo; detenerse si no puede garantizar el aislamiento.
- En Actions abrir el workflow y elegir `Run workflow`; documentar rama/sha/run ID, hora y conclusión. Para la prueba de BD en rama main seleccionar conscientemente `preflight_0034=false`. Para el workflow de archivos no hay inputs.
- Comprobar en logs BD los hitos reales `RESTAURACION_VERIFICADA` y `BASE_ORIGINAL_INTACTA`; en documentos `DOCUMENTOS_RESTAURACION_VERIFICADA` y `VOLUMEN_ORIGINAL_SIN_CAMBIOS`. Guardar links a las ejecuciones y versiones de archivos; nunca copiar secretos ni datos sensibles.
- Para **gate integral** elaborar backup pareado reciente y restaurarlo en entorno efímero separado: `alembic_version`, expedientes/documentos por tenant, rutas, hashes por archivo, ausencia de faltantes/duplicados, control RBAC, checkout autorizado y lectura real de una muestra de documentos; verificar SHA256 de cada contenedor y limpieza de ambas copias efímeras. Repetir migración 0039 y rollback en base restaurada sin alterar origen.
- Aprobación de responsable de seguridad después de verificar todas las evidencias. CI 5/5 no sustituye el gate documental.

## Herramienta pendiente
La conexión GitHub actual permite inspeccionar runs y logs pero **no expone workflow_dispatch**; requiere operador autorizado en la interfaz GitHub Actions (o una integración con permiso Actions:write), sin habilitarlo a ciegas.

**Decisión:** S NO aprobada todavía; I — INTEGRAR y D — DESPLEGAR bloqueados.
