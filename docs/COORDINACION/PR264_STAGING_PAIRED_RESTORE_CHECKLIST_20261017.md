# PR #264 — Protocolo operativo para ensayo pareado en staging aislado

## Estado de autorización
**Documento de preparación exclusivamente. NO ejecutar, no permitir SSH, no VPS ni producción.** La matriz GitHub Actions usa PostgreSQL efímero y archivos sintéticos; no equivale a una prueba de restauración real en staging.

## Precondiciones con evidencias obligatorias
1. Identificar por escrito al propietario del staging y un autorizador independiente; delimitar día, ventana y alcance.
2. Acreditar aislamiento físico/lógico del origen y destino: host distinto al de producción, credenciales propias, redes aisladas, volúmenes independientes, nombre de base diferente, sin DNS/puertos de producción ni secretos compartidos. Verificar de forma independiente la configuración de contenedores, almacenes y servicios; el nombre del environment no constituye evidencia.
3. Confirmar que no hay trabajos activos de escritura en staging, y que el intervalo de congelamiento de escrituras cubre **ambos** respaldos; documentar inicio/fin y lote común. Un pg_dump sin snapshot consistente del volumen no garantiza paridad temporal de adjuntos.
4. Capturar backup DB de staging y almacenamiento de documentos del **mismo lote**, manifiesto firmado/gestionado con hash SHA256 del dump, tar y hash/tamaño de cada archivo. Rechazar symlinks, rutas absolutas, rutas con .., archivos especiales, duplicados, archivos sin hash y tar de expansión descontrolada.
5. Confirmar destinos efímeros VACÍOS y diferentes del origen; asegurar UID no privilegiado, cuota, límite de tiempo, no sobrescritura, traza de eliminación; habilitar environment de aprobación manual **solo después** de análisis de riesgo.
6. Validar esquema real `tenants/expedientes/documentos`, `ruta_storage`, referencias opcionales, archivos huérfanos y políticas de disposición; registrar totales agregados y discrepancias sin datos privados.
7. Ejecutar RBAC con cuentas sintéticas de dos tenants sobre la aplicación RESTAURADA; comprobar 200 legítimo, 401/403 indebido, aislamiento de documentos y ausencia de fuga intertenant.
8. Ejecutar migración Alembic `0038 -> 0039 -> 0038 -> 0039` **únicamente en base restaurada**, con control de versión e integridad antes/después.
9. Simular falla de aplicación y de restauración, así como interrupción y recuperación; probar borrado de DB/archivos efímeros, revocación de credenciales y rollback sin tocar origen.
10. Adjuntar logs redactados, SHA256, recuentos, evidencias de limpieza, aprobaciones y firma de un revisor distinto del operador.

## Riesgos que impiden cerrar S
- Los checks sintéticos no prueban continuidad/sincronización de backups de staging ni validez de material de producción.
- No se ha demostrado aislamiento remoto del staging ni acceso restringido exclusivo.
- Las cifras históricas de DB 687 vs 2305 documentos y el tar de 654 ficheros se refieren a backups de fechas distintas; comparar requiere identificar lotes contemporáneos, no inferir pérdida.
- Verificar un tar antes de extraer no garantiza seguridad si el artefacto cambia entre inspección y extracción; conservar copia inmutable con hash, extraer sin privilegios en directorio desechable.
- Eliminación por trap ante fallo controlado no cubre SIGKILL, caída de runner/host y recursos externos persistentes. Exigir inventario, TTL y mecanismo externo de limpieza.

## Gate
**S abierta. I y D no autorizadas.** PR #264 permanece draft, sin fusión ni despliegue.
