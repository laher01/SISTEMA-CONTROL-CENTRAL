# PR #264 — Puerta S: comprobación de controles de archivos y recursos efímeros

Fecha: 2026-10-17. Solo ensayos sintéticos en GitHub Actions.

## Controles añadidos
- Extracción TAR mediante copia privada revisada con SHA256 y tope de bytes; archivos nuevos abiertos con `O_EXCL` y `O_NOFOLLOW`, rechazo de rutas especiales, verificación de tamaño y SHA256 al escribir; borrado de salida parcial tras excepciones controladas.
- Limpieza de directorios de pruebas sintéticas en modo inspección por defecto, marca de propiedad exacta, mínimo TTL de una hora, exclusión de symlinks internos, montajes y PID de proceso activo.
- Pruebas sintéticas offline para un PID activo y directorios con symlinks internos.

## Límites no resueltos
- No garantiza inmunidad frente a TOCTOU si otro proceso cambia un componente del directorio entre verificaciones. Para staging remoto se necesitan `dirfd`, `openat` y `O_NOFOLLOW` en **cada** nivel o aislamiento efectivo e inmutabilidad demostrable.
- Ningún método `trap` verifica apagados abruptos `SIGKILL`, caída del runner/host o limpieza de recursos externos. El reconciliador todavía no es un servicio persistente.
- Un marcador en JSON y PID no constituye propiedad autenticada: procesos podrían reutilizar PIDs. Para aplicación real requieren identidad de ejecución, aislamiento de directorios, leases, límites de almacenamiento y confirmaciones.
- Los límites TAR no sustituyen cuotas de CPU, memoria, I/O, archivos ni resistencia a archivos comprimidos maliciosos.
- El preflight previo solo valida cadenas/rutas localmente; **no** certifica DNS, host, red, permisos, volúmenes ni secretos distintos de producción.

## Aprobación S
Exige recuperación pareada real de DB y documentos del mismo lote en un staging separado verificable, pruebas RBAC y conciliación sobre esa copia, fallo y rollback supervisados, revisión de seguridad independiente. Hasta entonces **S abierta; I y D bloqueadas**. No acceder VPS, no fusionar ni desplegar.
