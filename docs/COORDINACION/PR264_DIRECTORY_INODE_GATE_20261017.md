# PR #264 — Rollback de directorios, evidencia y gate S

Fecha de trabajo: 17/10/2026. **Solo GitHub Actions sintético, sin VPS ni staging remoto.**

## Línea base
Commit `4d4af17b019bbb4c9cc464883573ef89b0166003`: 6/6 workflows completados con SUCCESS. PR #264 DRAFT.

## Cambios
- `deploy/recovery_safe_extract.py` registra `st_dev`/`st_ino` de los directorios recién creados y los compara antes de `rmdir` en rollback, utilizando el descriptor del padre.
- Prueba adversarial de sustitución del inode del directorio, que debe conservar el reemplazo ajeno. Prueba existente de desaparición del padre adaptada a la nueva estructura de inventario.
- Se mantiene el control previo de identidad de archivos con `stat(..., follow_symlinks=False)`, y la señal explícita de fallo de limpieza/cuarentena.

## Riesgos abiertos
La comprobación de identidad antes del `unlink/rmdir` **no es atómica**: sigue existiendo ventana TOCTOU ante un escritor adversario con acceso al directorio. La prueba sintética es controlada y no prueba host compartido. Para proteger staging se necesitan directorios y montajes exclusivos, UID dedicado, cuotas, límites de CPU/memoria/I/O, prohibir escritores concurrentes, mecanismo externo de reconciliación ante SIGKILL, respaldos DB/documentos de mismo lote y revisión independiente.

La herramienta `deploy/recovery_orphan_cleanup.py` continúa `dry-run` por defecto y no debe usarse para borrar datos reales. Su marcador JSON no autentica propiedad. Se conservan recursos con PID y los marcados como symlinks/montajes.

## Gate
**S OPEN / I BLOCKED / D BLOCKED** hasta ensayo pareado aislado y autorizado en staging real, RBAC y tenant checks con restauración verdadera, revisión de integridad y evidencia de limpieza. PR #264 debe seguir draft y PR #208/#237/#249 sin cambios. No merge, VPS ni deploy.
