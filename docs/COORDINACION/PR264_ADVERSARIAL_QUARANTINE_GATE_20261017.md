# PR #264 — Controles adversariales y gate S (17/10/2026)

## Verificaciones
La versión anterior `311bc0b8e0531f368d02c8c5163aa3be2cc614e9` tenía 3 controles de seguridad SUCCESS; backend, roles y recepción seguían in_progress al consultarlos. No inferir CI verde sin resultado final.

## Correcciones de esta iteración
- `deploy/recovery_safe_extract.py`: si el rollback encuentra una ruta alterada, eliminada o un conflicto de permisos, lanza un error explícito de **rollback incompleto / destino en cuarentena**, sin afirmar que los archivos parciales hayan sido eliminados.
- Test adversarial de fallo concurrente inyectado durante apertura mediante dirfd y posterior falla de rollback.
- Test de límite de bytes del archivo TAR comprimido antes de extraer contenidos; destino permanece vacío.
- La limpieza de recursos huérfanos sigue dry-run por defecto, no toca bases de datos, excluye recursos PID y rechaza symlinks/montajes.

## Riesgos pendientes
1. `RuntimeError` de cuarentena es una señal de error, NO un mecanismo de aislamiento operativo de carpetas o procesos. Diseñar directorio exclusivo con etiquetas de lote, escrituras bloqueadas y operador responsable.
2. El rollback falla cerradamente si la estructura cambia; aún faltan pruebas de inodos sustituidos bajo carrera real, límites de tiempo/CPU/archivos, ejecución no privilegiada y bloqueo de filesystem compartido.
3. El limpiador no usa identificador autenticado de ejecución ni reconciliación externa tras SIGKILL o caída de runner.
4. Staging necesita aprobación humana independiente, controles de aislamiento de red/host/secretos/volúmenes, backup de DB y archivos del mismo lote, ensayos RBAC y conciliación en copia real restaurada.

**S ABIERTA, I/D BLOQUEADOS.** PR #264 DRAFT. Ninguna acción sobre VPS, main ni despliegue.
