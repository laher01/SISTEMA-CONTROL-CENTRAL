# PR #292 — Runbook de preintegración, respaldo y recuperación

**Documento preparatorio. No ejecutar sobre VPS ni producción sin autorizaciones específicas.**

## 1. Control de versión y ramas

1. Registrar SHA completo de `main`, HEAD del PR #292, SHA de merge-base, lista de archivos y migraciones Alembic aplicables.
2. Actualización MISD PR #388 (SHA `ff029323d6e10e6558b00bf09b30725586be7bc1`): rama de ensayo derivada de `main` SHA `1fc1aef1ac25afa1ad3bc28098e85f5756bfe1a1`, comparación registrada 39 commits por delante y 0 detrás. `0041` procede de `main` y `0042` declara `down_revision = '0041'`; CI comprobó `upgrade head`, `downgrade -1` y `upgrade head` en base desechable. Revalidar HEAD, grafo y aprobaciones antes de integración; el downgrade `0042` elimina la tabla de solicitudes y no es estrategia segura para datos reales.
3. No rebasar, fusionar, ni pisar cambios de Etapa 7/landing sin revisión del responsable. Reejecutar CI después de resolver divergencia en rama de integración aislada.
4. Confirmar aprobaciones de propietarios de módulos MISD, Responsable/pagos, Rol Gestor, OCR/PDF y seguridad SaaS.

## 2. Aislamiento indispensable

- Preparar **staging distinto de la VPS productiva**, con PostgreSQL y almacenamiento independientes. No reutilizar `VPS_HOST`, datos reales, secretos, rutas ni volumen de producción.
- Generar conjunto anonimizado sintético con expedientes, GRE, referencias, vouchers, pagos, documentos previamente retirados, alertas, solicitudes MISD y distintos tenants.
- Verificación del archivo `.github/workflows/deploy-staging.yml` en `main` (SHA inspeccionado arriba): **no tiene disparador `push`**. Declara `pull_request` solo para cambios del propio workflow y `workflow_dispatch`; su job remoto `deploy` exige simultáneamente `workflow_dispatch` y `refs/heads/main`, más validaciones previas. Esta inspección NO acredita otros workflows, webhooks, servicios externos o reglas de protección. Antes de integrar, inventariarlos y verificar el efecto real de la fusión; no asumir que el nombre «staging» garantiza aislamiento.

## 3. Copia de seguridad — pasos a comprobar en staging

1. Guardar SHA de binarios, versión Docker/PostgreSQL, versión y `alembic current/heads/history`; sin imprimir secretos.
2. Realizar backup consistente PostgreSQL con `pg_dump --format=custom --no-owner --no-acl` utilizando conexión y secretos de **staging**, a directorio restringido. Registrar tamaño y hash SHA-256, usuario operador y hora.
3. Copiar por separado originales documentales, configuración no secreta y manifiesto de rutas; calcular hashes de muestras, inventario y conteos por tenant.
4. Ensayar restauración a **base nueva, aislada, vacía** mediante `pg_restore --exit-on-error --no-owner --no-acl`; restaurar archivos a volumen aislado y comprobar FK, índices, SHA, conteos, expedientes, pagos, GRE y auditoría. No sobrescribir base usada.
5. Comprobar migraciones `upgrade` y reversión permitida `downgrade` en copias, con muestras de estados y auditoría antes/después. Si downgrade implica pérdida de datos, marcarlo no apto y restaurar snapshot como recuperación.
6. Medir y registrar RTO/RPO observados y disponibilidad de rollback, nunca inventar tiempos.

## 4. Ensayo de fallos y recuperación

- Cortar un paso de migración deliberadamente en staging, verificar rollback o restauración completa.
- Simular original documental ausente/corrupto, dos restauraciones concurrentes, y simultaneidad pago/retirada **ambos órdenes** con mutex intermodular validado.
- Verificar que registros fiscales y pagos no se eliminan físicamente y que auditoría conserva antes/después.
- Después de recuperar, confirmar: `/health`, permisos por tenant y rol, documentos originales, expedientes, GRE, vouchers, saldos, alertas y cola de mantenimiento.

## 5. Puertas de decisión

**No integrar** si falta uno: (a) carreras pago/retirada resueltas con pruebas PostgreSQL, (b) revisión de conflictos y CI del SHA definitivo, (c) aprobaciones de responsables, (d) restauración real ensayada y registrada, (e) políticas legales de conservación.

**No desplegar** sin autorización separada para el efecto automático de `push main`, recuperación validada y una ventana de operación con persona responsable.

## Evidencias pendientes

- En la evaluación del PR #388, GitHub Actions sí ejecutó `alembic upgrade head`, `downgrade -1`, `upgrade head` en una base desechable. **No** se ha acreditado aquí `pg_dump`, `pg_restore`, restauración de originales, SSH ni validación de la VPS.
- Este runbook no certifica respaldos actuales ni garantiza recuperación de producción.

## Puertas de seguridad verificadas y pendientes — PR #388

- CI del SHA `ff029323d6e10e6558b00bf09b30725586be7bc1`: 8/8 workflows `success`; 639 tests backend aprobados y 10 advertencias. Incluye regresiones de permisos, tenant y concurrencia PostgreSQL, sin sustituir revisión semántica humana.
- PR #388: sin revisiones aprobatorias ni hilos de revisión. PR #292: cuatro hilos abiertos; PR #336: dos hilos abiertos. Resolverlos solo tras revisión y autorización de sus responsables.
- No se ha verificado mediante este conector la configuración efectiva de protecciones/rulesets de `main` ni se ha inventariado exhaustivamente el CD externo: **bloqueo para integración** hasta aportar evidencia.
- Evidencia obligatoria de respaldo/restauración aislada: salida de `pg_dump` y `pg_restore --exit-on-error`, hash de copia y originales, conteos por tenant, integridad de FK, documentos fiscales protegidos y prueba de recuperación, con datos de ensayo, fuera de producción.
- **No fusionar ni desplegar** durante la auditoría; ninguna aprobación de CI sustituye el consentimiento para esas operaciones.
