# PR #264 — Revisión de preflight, TAR y limpieza (17/10/2026)

**Rama aislada; no ejecutar en VPS, no fusionar, no desplegar.**

## CI base
Commit `ee9e933584d3afcef00896f7263c665c49cf863a` tenía 5/6 workflows SUCCESS y `roles-real-integration` aún en curso en la primera revisión. No afirmar 6/6 hasta confirmar su estado.

## Mejoras de este ciclo
1. `deploy/recovery_safe_extract.py` mantiene copia temporal privada del TAR validado, vuelve a comprobar SHA256, limita bytes comprimidos y controla tipo/ruta/hash/tamaño de cada fichero al extraer. Limpia productos parciales si ocurre una excepción controlada.
2. `deploy/recovery_orphan_cleanup.py` solo selecciona carpetas con marcador explícito `.factcentral-synthetic-restore.json`, tipo `factcentral-ci-ephemeral`, nombre coincidente y TTL mínimo 3600 s. Sin `--apply` únicamente informa. **Este script nunca elimina bases de datos**, opera sobre ficheros sintéticos de un directorio expresamente autorizado.
3. Las pruebas negativas verifican traversal, enlace simbólico, modificaciones del TAR, destino no vacío y limpieza selectiva. Son pruebas sintéticas.

## Riesgos residuales críticos
- El cambio entre el `stat` y la apertura del archivo de origen, o la mutación concurrente del destino y sus directorios, exige almacenamiento privado sin escritores concurrentes y controles basados en descriptores (`openat`, `O_NOFOLLOW`) antes de permitir ejecución remota. Una copia temporal no prueba por sí misma inmutabilidad frente a otros procesos privilegiados.
- La limpieza programada por TTL requiere prueba adicional contra marcas falsificadas, montajes externos, PID activo y ciclos de borrado concurrentes. **No activar `--apply` en entornos compartidos**.
- El `trap EXIT` y su test de falla controlada no cubren SIGKILL, fallos de host ni recursos remotos; exigir reconciliación externa y registro de recursos por lote.
- Limitar tamaño TAR sin cuotas del contenedor, memoria, CPU e I/O no evita agotamiento completo de recursos.
- `recovery_staging_preflight.py` compara cadenas de host y rutas; esto NO acredita aislamiento físico/lógico, DNS/IP y secretos. Se exige evaluación independiente de los recursos reales.
- Aún faltan prueba de respaldo pareado del mismo lote en staging, conciliación de documento-expediente-tenant con datos de ese lote y revisión de seguridad humana.

## Gate
Mantener PR #264 DRAFT. S ABIERTA, I/D bloqueadas. Requerir aprobación específica antes de acceso a staging/VPS, además de evidencias de hosts/volúmenes/credenciales aislados y rollback.
