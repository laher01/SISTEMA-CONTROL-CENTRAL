# PR #264 — Seguridad de TAR y preparación del ensayo staging

Fecha: 2026-10-17. **No se ejecutó ninguna acción remota ni se habilitó el acceso a la VPS.**

## Resultado de auditoría
- Base inicial: commit `e258008c313121eb6ede6ab8517974bd0d0bed1e`, seis workflows SUCCESS.
- La extracción anterior `tar -xzf` del ensayo sintético fue sustituida por `deploy/recovery_safe_extract.py`: valida digest del artefacto, inventario de archivos, tipos y rutas TAR, recuento y expansión declarada mediante auditor, destino desechable vacío y bytes/hash/tamaño de cada archivo extraído.
- Se añadieron pruebas offline: rutas relativas peligrosas, TAR con enlaces simbólicos, archivo alterado, destino no vacío y destino symlink.
- El código NO se considera todavía un extractor general apto para staging con operadores no confiables: la validación y lectura ocurren en aperturas distintas y existe riesgo TOCTOU si alguien puede cambiar el TAR o los componentes de ruta. Los directorios padres y ficheros deben pertenecer a un usuario aislado sin escritores concurrentes, o usar descriptor inmutable; extracción no privilegiada, límites de CPU/memoria y cuotas; no promocionar carpetas parciales tras fallo.
- `trap EXIT` verifica fallo inducido; **no prueba** SIGKILL, caída de runner, corte de red/energía ni residuos externos.

## Matriz de riesgo priorizada
| Riesgo | Severidad | Mitigación y evidencia faltante |
| --- | --- | --- |
| Origen staging comparte recursos con producción | Crítica | Inventario de redes/hosts/volúmenes/secretos y revisión humana independiente |
| Respaldos PG + documentos de distinto momento | Crítica | Pausa de escrituras o snapshot consistente con ID único y marcas de tiempo |
| TOCTOU/symlinks en extracción | Alta | Artefactos inmutables, contención de directorios, cuotas, límites y pruebas adversariales |
| Archivos referenciados faltantes o cruzados entre tenants | Alta | Cotejo completo SQL y hashes de ruta_storage contra volumen restaurado, sin datos personales en logs |
| RBAC de usuarios reales difiere de test sintético | Alta | Cuentas sintéticas en staging restaurado y 200/401/403; no utilizar contraseñas de producción |
| Limpieza interrumpida tras kill o caída | Alta | TTL/reconciliador independiente y evidencia de destrucción DB/volumen/credenciales |
| Incompatibilidad migraciones/rollback | Alta | `0038→0039→0038→0039` solo en copia efímera y checksum/recuento antes/después |
| Diferencia histórica backups DB 687/2305 vs TAR 654 | Media | Alinear lote y fecha; no inferir pérdida ni comparar tamaños de snapshots inconexos |

## Criterios de gate S
1. Revisión del workflow remoto independiente con credenciales exclusivamente staging, explicitación de host/destino, aprobación manual y rechazo de destinos peligrosos.
2. Ensayo pareado real en staging aislado, con backups mismo lote, manifiestos SHA256 y restauración en recursos efímeros sin escrituras al origen.
3. Evidencia de hashes por archivo, relaciones documento-expediente-tenant, RBAC y roundtrip Alembic.
4. Simulación de fallo/rollback y **limpieza incluso ante terminación abrupta** demostrada.
5. Revisión independiente de logs, diferencias, aislamiento, plan de reversión y firma del responsable de seguridad.

Hasta entonces **S ABIERTA, I/D BLOQUEADAS; PR #264 DRAFT**. No merge, no VPS, no deploy.
