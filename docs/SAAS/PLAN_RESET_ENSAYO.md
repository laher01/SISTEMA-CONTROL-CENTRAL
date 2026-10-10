# Reconstrucción controlada de FACT CENTRAL (solo datos de ensayo)

## Auditoría del entorno (no destructiva)

El repositorio declara `deploy/docker-compose.production.yml`, PostgreSQL 17, volúmenes `fact_central_staging_pgdata` y `fact_central_staging_documentos`, y `POSTGRES_DB` configurable en `deploy/.env.production`. **Son declaraciones, no prueban que la VPS esté ejecutándolas**. Debe verificarse por SSH en el servidor autorizado, nunca inferir el nombre de la base por `FC_DATABASE_URL` predeterminado.

Ejecutar desde la raíz del repositorio en VPS de **pruebas**:

```bash
bash deploy/audit-backup-pre-reset.sh
```

Registrar el archivo `BACKUP_VERIFICADO`. Probar restauración antes de cualquier limpieza:

```bash
bash deploy/validate-restore-pre-reset.sh deploy/backups/pre_reset/factcentral_FECHA.dump
```

Aceptar únicamente si devuelve `RESTAURACION_VERIFICADA`, con un número de tablas coherente con el inventario previo. Resguardar aparte el volumen de documentos y comprobar archivos y hashes: el dump de PostgreSQL NO contiene los binarios guardados en `fact_central_staging_documentos`. Guardar una copia externa y verificar el archivo antes de borrar.

## Identidad SaaS

`SUPADMIN01` pertenece al tenant reservado `PLATFORM` (código fijo), no al tenant de NEXOMAR. El inicio de sesión global requiere seleccionar explícitamente el espacio `PLATFORM` hasta que exista portal global separado. `ADMIN01` sigue perteneciendo a su tenant de NEXOMAR y su hash de contraseña **no se modifica**. No recrear ni resetear ADMIN01.

## No ejecutar aún un borrado

1. Registrar nombre, host y huella del clúster de pruebas, lista de tablas, migración Alembic actual y conteos de registros.
2. Obtener dump no vacío, SHA-256 correcto, restauración exitosa en base efímera y copia comprobada de documentos.
3. Exigir verde en lint, format, mypy, pytest, tests frontend y probar migración 0016 + altas `PLATFORM` en una copia de la base.
4. Confirmar por pruebas: SUPADMIN01 y ADMIN01 en distintos tenants, hashes inalterados, 403 para usuarios sin permiso y ausencia de datos cruzados.
5. Solo entonces preparar un comando de reinicialización que requiera nombre exacto de la base, una confirmación manual, y nunca alcance `main`, tokens de Cloudflare ni volúmenes externos.

No se ha ejecutado ningún borrado ni restauración real en VPS desde esta conversación.
