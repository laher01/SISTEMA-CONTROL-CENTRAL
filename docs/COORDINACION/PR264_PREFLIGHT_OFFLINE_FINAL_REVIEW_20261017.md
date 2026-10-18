# PR #264 — Revisión final de preflight y límites pendientes

Fecha: 17/10/2026. Trabajo exclusivo sobre rama aislada, sin ejecución remota.

## Evidencia de origen
El commit `0a428e3813750d4e7a4f1f7a525d6dc1098d4dcc` tiene **6/6 workflows SUCCESS** en GitHub Actions.

## Endurecimiento adicional
- Preflight `deploy/recovery_staging_preflight.py` rechaza carpetas fuente/destino symlink, padres symlink e identificadores de host o base de datos vacíos; el check de destino vacío y de rutas disjuntas sigue vigente.
- Pruebas negativas `deploy/test_recovery_staging_preflight.py` reproducen estos casos.
- Se mantienen reglas de no ejecutar contra VPS, no modificar `main`, no fusionar y no desplegar.

## Advertencias bloqueantes para el gate S
1. Estas comprobaciones de texto y filesystem local **no certifican** la separación de redes, hosts, volúmenes ni credenciales del entorno real.
2. El extractor `recovery_safe_extract.py` usa `O_NOFOLLOW` para archivos finales, pero aún no abre **cada componente** del directorio con descriptores anclados. No está certificado contra adversarios con escritura concurrente sobre los directorios de recuperación.
3. El limpiador de recursos huérfanos es local y sintético; un PID puede reciclarse, y un marcador no autentica la propiedad. Los fallos abruptos de runner no están cubiertos por el trap del proceso.
4. Para completar S: staging remoto realmente aislado y autorizado, respaldo de datos+archivos del **mismo lote**, restauración pareada con evidencia, RBAC sobre el backend restaurado, coherencia tenant y archivos, reversión/limpieza, y aprobación de seguridad independiente.

**S ABIERTA, I/D BLOQUEADOS.** El PR #264 debe conservarse en borrador.
