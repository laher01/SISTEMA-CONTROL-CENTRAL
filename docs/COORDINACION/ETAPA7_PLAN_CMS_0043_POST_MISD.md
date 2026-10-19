# Etapa 7 — conciliación CMS 0043 con MISD 0042

Estado: propuesta coordinada, SIN FUSIONAR NI DESPLEGAR.

## Evidencia
- PR #313: migración CMS `20261018_0042_cms_landing_versiones.py` con `revision=0042`, `down_revision=0041`.
- PR #336 (responsabilidad MISD): `20261019_0042_solicitudes_retiro_misd.py` con `revision=0042`, `down_revision=0041`.
- PR #349: rama TEST ONLY con CMS `0043`, dependiente de MISD `0042`; CI backend, recepción, roles y migraciones 4/4 SUCCESS en SHA `5ddb95926b210c94e4be6bae42d1c9e1db8d7091`.
- PR #348: preservación de estado, versión y auditoría durante 0041, CI 3/3 SUCCESS en SHA `5a3785f8e6138d2823e1f4798fe03690d0c481b0`.
- main verificado: `e24599110f95b2f089fffd54ae013f827d3ae7ef`, sin MISD 0042.

## Decisión técnica
1. No modificar migraciones ni código de MISD y no fusionar PR #349.
2. Mantener PR #313, #316 y #319 en borrador mientras MISD #336 y su base #292 no estén integrados/aprobados.
3. Una vez exista 0042 MISD en la base de integración autorizada, **solo en rama CMS** sustituir el archivo CMS 0042 por `20261019_0043_cms_landing_versiones.py`; usar `revision = "0043"` y `down_revision = "0042"`. No mantener simultáneamente ambas revisiones CMS ni alterar 0042 MISD.
4. Actualizar PR #313, después #316 y #319 respetando commits, bases y revisión del responsable. Exigir nuevos CI sobre los SHA definitivos.
5. Verificar un solo head Alembic y PostgreSQL limpio: upgrade hasta 0042, posterior 0043; conservar TRUE/FALSE, versión y auditoría; comparar metadatos y probar rollback.
6. Regresión de acceso 401/403, versión 409, concurrencia PostgreSQL y contenido público fail-closed. Mantener snapshot publicado estable como bloqueante pendiente identificado en auditoría #319.
7. Separar integración (I) de despliegue (D), con respaldo/restauración verificados y autorizaciones específicas.

**No convertir la evidencia aislada #349 en código de producción.** Esta propuesta documental no afirma haber certificado aún la combinación definitiva #313/#316/#319 con MISD.
