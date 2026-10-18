# PR #264 — Gate S: descriptores TAR y recursos huérfanos (17/10/2026)

## Evidencia inicial
Commit `0a428e3813750d4e7a4f1f7a525d6dc1098d4dcc`: 6 workflows GitHub Actions SUCCESS. Se mantiene PR #264 DRAFT.

## Cambios de este ciclo
- Extracción de TAR sintético con `dir_fd`, `O_DIRECTORY`, `O_NOFOLLOW`, `O_EXCL` y archivos de permisos 0600; escritura incremental limitada a la longitud del manifiesto y SHA256 por fichero; los directorios creados se rastrean para rollback de fallo manejado.
- El respaldo se copia a almacenamiento temporal privado antes de la inspección y la extracción; se compara digest SHA256 del archivo copiado.
- Limpiador offline permanece dry-run por defecto y rechaza **cualquier recurso con marcador PID** (vivo, muerto o reutilizado): una comprobación `kill(pid,0)` sola no valida identidad del proceso.
- Prueba negativa para carpeta antigua con PID ya desaparecido, que debe mantenerse.

## Riesgos y verificaciones aún abiertas
1. Los componentes del destino anteriores al descriptor de raíz y cualquier escritor con acceso al mismo directorio no quedan protegidos contra mutaciones arbitrarias. Exigir contenedor, UID exclusivo, `mount namespace`, no compartir rutas y políticas de límite de disco, CPU y memoria.
2. El rollback de archivos creados debe fallar cerradamente si otro proceso altera directorios; no garantiza limpieza después de `SIGKILL` o apagado del host. Se necesita reconciliación externa respaldada por manifiesto autenticado, no solo marcador JSON.
3. Si el servidor de staging tiene recursos compartidos con producción, prohibir ensayo remoto. Los preflight de rutas/host **no** demuestran aislamiento lógico ni de secretos.
4. El ensayo conjunto DB+documentos debe usar backup del mismo lote consistente; verificar correspondencia real SQL-documentos por tenant y RBAC en la copia recuperada.
5. El pase CI solo valida material sintético en GitHub Actions. S sigue ABIERTA, I/D BLOQUEADOS.

No acceso VPS, no merge, no deploy. PR #208/#237/#249 intactos.
