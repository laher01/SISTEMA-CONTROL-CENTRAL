# PR #264 — Protección de inodos en rollback (17/10/2026)

## Línea base comprobada
Commit `a66f9c463c53ebda959b06c4c7eb1f41b0836c00`: seis workflows SUCCESS, incluidos PostgreSQL 16/17, auditoría offline, coordinación, backend, RBAC y recepción.

## Cambio de código
El extractor `deploy/recovery_safe_extract.py` registra dispositivo e inode de los archivos que crea. Antes de ejecutar `unlink` en un rollback compara la identidad y verifica que siga siendo un archivo regular. Si otro archivo ha sustituido al original, falla cerradamente sin borrar ese sustituto y exige cuarentena/revisión del destino. Pruebas incluidas de reemplazo atómico vía `os.replace` y eliminación permitida del inode legítimo.

## Alcance y riesgos
- La comprobación `stat` anterior al `unlink` reduce riesgos, pero **no elimina la carrera TOCTOU** entre ambas operaciones frente a un escritor con control simultáneo del directorio. No afirmar protección completa de inodos, ni usar en staging compartido.
- El rollback de directorios todavía necesita una política de identidad y exclusividad; una alteración concurrente puede impedir el rollback.
- El limpiador huérfano conserva `dry-run` y la regla de no borrar recursos marcados con PID. Su marcador JSON no constituye autenticación de propiedad.
- Límites de bytes comprimidos, archivos expandidos y recuento TAR no sustituyen límites de CPU/memoria/I/O ni un entorno aislado.
- Gate S exige restauración pareada real de DB+documentos del mismo lote en staging demostrablemente aislado, pruebas RBAC/tenants y reversión, reconcilación de recursos tras terminación abrupta y revisión independiente.

**S OPEN; I/D BLOCKED; PR #264 DRAFT. Sin VPS, fusión ni despliegue.**
