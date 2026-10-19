# RC-1 — Empaquetado conjunto controlado (sin producción)

## Alcance comprobable
`deploy/package_restoration_pair.py` recibe un dump **ya generado** y un directorio documental **ya estable**; los copia a un directorio nuevo privado, registra SHA-256 y publica con `RENAME_NOREPLACE` de Linux. Los tests usan archivos ficticios. La prueba de restauración debe realizarse después en una PostgreSQL aislada y contrastarse con `export_restored_manifest.py` y `check_restored_pair.py`.

## Barrera de escritura OBLIGATORIA antes de generar el par
1. Operador autorizado programa ventana y verifica que todos los escritores estén detenidos: API/backend, trabajadores de correo, tareas programadas, cargas y cualquier otro proceso que escriba documentos o registros.
2. Comprobar que no hay cargas en curso, transacciones relevantes sin finalizar o procesos externos. **La utilidad NO detiene ni inspecciona escritores**, y su marca `--escritores-detenidos` solo es una declaración del operador, no una prueba criptográfica.
3. Con barrera activa, generar dump PostgreSQL verificable y obtener directorio/instantánea documental estable. Registrar hora, responsables, identificador de captura y evidencias independientes en gestor seguro.
4. Sobre **copias aisladas**, ejecutar `python3 deploy/package_restoration_pair.py --dump-restaurable /aislado/copia.dump --documentos-estables /aislado/documentos --salida-nueva /aislado/paquete --escritores-detenidos`.
5. Restaurar contenido de `postgres.dump` en una base nueva aislada y `documentos.tar` en un volumen nuevo mediante herramientas de los PR #333 y #345. Exportar manifiesto desde DB RESTAURADA, comparar por tenant/ruta/sha256 y verificar conteos.
6. Registrar resultados, análisis de discrepancias, duración de recuperación y SHA de las dos copias. No pasar a I/D sin evidencias suficientes.

## Bloqueantes reales
- La coordinación operacional de escrituras, snapshot consistente y respaldo cifrado **no están automatizados**. Esta herramienta NO constituye por sí sola respaldo de producción consistente ni una restauración verificada.
- El archivo `postgres.dump` no se verifica como formato PostgreSQL dentro de esta herramienta. Debe validarse con `pg_restore --list` y ejecutar restauración aislada.
- No hay integración en `deploy-staging.yml`, ni acceso a VPS, ni secretos guardados en Git, ni política implantada de cifrado/retención externa.
- Hasta resolver estos puntos, la versión candidata RC-1 **no tiene autorización de despliegue**.
