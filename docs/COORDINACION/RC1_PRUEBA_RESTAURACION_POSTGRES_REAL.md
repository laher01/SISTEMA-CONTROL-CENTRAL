# RC-1 — Prueba de restauración real aislada (pendiente de ejecución)

**Objetivo:** pasar de fixtures a una base PostgreSQL 17 restaurada mediante `pg_restore` y cotejar archivos reales de prueba, nunca datos productivos.

## Precondiciones obligatorias
- PostgreSQL de laboratorio aislado y credenciales limitadas, sin acceso a la VPS; `pg_dump`, `pg_restore`, `psql` y Python con psycopg disponibles.
- Solo un dump **sintético o anonimizado autorizado** y un volumen documental de prueba estables.
- Base de destino nueva `factcentral_restore_*`; confirmar que host/puerto corresponden al laboratorio. No usar URL productiva ni reutilizar un destino existente.
- No guardar contraseñas en logs ni Git.

## Procedimiento verificable
1. Crear datos de laboratorio consistentes con `documentos(tenant_id, ruta_storage, sha256)`, donde el SHA-256 coincida con el contenido de archivos bajo `tenant_uuid/prefijo_sha/sha256`.
2. Capturar la BD con `pg_dump --format=custom` y documentos desde origen inmóvil. Guardar hashes y evidencia de barrera contra escritores. Validar dump mediante `pg_restore --list`.
3. Crear una segunda base **nueva** de laboratorio `factcentral_restore_*`; aplicar `pg_restore --exit-on-error --no-owner --no-acl`. Comprobar `alembic_version`, conteo documental y migraciones compatibles.
4. Restaurar `documentos.tar` usando `document_archive_isolated.py restore` a una ruta nueva aislada.
5. Exportar manifiesto desde **la segunda base** con `export_restored_manifest.py`, registrar `REGISTROS_RESTAURADOS`, y comparar con `check_restored_pair.py` por tenant, ruta, SHA-256 y número de registros.
6. Introducir un caso de documento ausente, un documento alterado y un tenant cruzado en otro par **ficticio**; deben provocar fallos de cotejo. La prueba positiva debe obtener cero diferencias.
7. Registrar SHA del dump y TAR, SHA de commit, duración, pruebas ejecutadas, resultado, fallos, limpieza del entorno y responsables.

## Condiciones de rechazo
- El hecho de que una prueba ficticia de Python pase **no** prueba que `pg_restore` funcione.
- Si existen documentos referenciados ausentes, hashes diferentes, permisos incorrectos, rutas cross-tenant o discrepancias de cantidad, **bloquear** I y D.
- No ejecutar este procedimiento directamente en producción. No borrar bases o volúmenes productivos.
- Continúan pendientes el mecanismo automatizado de captura consistente, cifrado, custodia fuera del servidor y rollback operativo comprobado.

**Estado a 2026-10-19:** procedimiento documentado, sin evidencia de ejecución con una base PostgreSQL restaurada real en esta etapa.
