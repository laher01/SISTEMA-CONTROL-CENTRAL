# PR #292 — Runbook de preintegración, respaldo y recuperación

**Documento preparatorio. No ejecutar sobre VPS ni producción sin autorizaciones específicas.**

## 1. Control de versión y ramas

1. Registrar SHA completo de `main`, HEAD del PR #292, SHA de merge-base, lista de archivos y migraciones Alembic aplicables.
2. La comparación inicial de `main` contra la rama identifica tres commits de `main` pendientes; afectan `pagina_web.py`, `models.py`, landing frontend y añaden migración `0041`. El PR incorpora `0042` que declara `down_revision = '0041'`: **verificar orden y validez del grafo Alembic**.
3. No rebasar, fusionar, ni pisar cambios de Etapa 7/landing sin revisión del responsable. Reejecutar CI después de resolver divergencia en rama de integración aislada.
4. Confirmar aprobaciones de propietarios de módulos MISD, Responsable/pagos, Rol Gestor, OCR/PDF y seguridad SaaS.

## 2. Aislamiento indispensable

- Preparar **staging distinto de la VPS productiva**, con PostgreSQL y almacenamiento independientes. No reutilizar `VPS_HOST`, datos reales, secretos, rutas ni volumen de producción.
- Generar conjunto anonimizado sintético con expedientes, GRE, referencias, vouchers, pagos, documentos previamente retirados, alertas, solicitudes MISD y distintos tenants.
- Verificar que el pipeline `.github/workflows/deploy-staging.yml` tiene `push` a `main` y job de despliegue remoto. No integrar sin autorización específica del posible despliegue automático; no asumir que el nombre “staging” garantiza aislamiento.

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

- No se ha ejecutado `pg_dump`, `pg_restore`, `alembic upgrade/downgrade`, SSH ni validación en VPS en esta tarea.
- Este runbook no certifica respaldos actuales ni garantiza recuperación de producción.
