# FACT CENTRAL — Ensayo coordinado de recuperación (gate S)

Estado: **DISEÑADO, NO EJECUTADO**. Rama aislada de preintegración. No autoriza fusión o despliegue.

## Antecedentes verificables

- PostgreSQL: run 38684817279/job 116257152509, éxito el 15/10/2026. El respaldo restaurado contabilizó 2305 registros de documentos, la base origen leída en ese momento 687. El workflow no requiere igualdad ni certifica instantánea común. La discrepancia puede obedecer a cambio de base, momento, filtro o diferentes datos históricos; **no se determinó la causa**.
- Archivos: run 38028472484/job 114144245355, éxito el 10/10/2026: 654 archivos inventariados y 654 extraídos de respaldo; sin correspondencia de cada archivo con filas de la BD restaurada.
- Fechas y procedencias de los respaldos no forman un snapshot sincronizado. Los jobs existentes comprueban extracción/restitución parciales, no consistencia de referencia.

## Requisitos de un ensayo nuevo, aislado y autorizado

1. Operador verifica por separado que staging no comparte base de datos, contenedores, volúmenes ni montajes escribibles con producción. Nunca usar un volumen activo como destino de restauración. Si no se puede demostrar aislamiento, abortar.
2. En ventana controlada de staging, detener temporalmente las escrituras **solo en staging** y tomar un par de instantáneas bajo el mismo identificador de lote: dump PostgreSQL custom + copia de volumen documental. Recuperar servicios de staging después de la captura. Registrar hora de inicio/fin, entorno y `alembic_version`. No reutilizar copias 10/10 y 14/10 como un par.
3. Guardar ambas copias en almacenamiento de staging protegido con SHA256 y manifiesto de archivos regulares: rutas normalizadas relativas, tamaño y hash individual; rechazar symlinks, rutas absolutas, segmentos `..` y cualquier enlace capaz de salir del destino antes de extraer archivos comprimidos. No registrar contenidos sensibles.
4. Restaurar el dump en una **DB nueva desechable** y los archivos en un **directorio/volumen temporal independiente**. Sin conectar estos destinos al backend que atiende clientes. Verificar checksum del contenedor de respaldo, conteo de filas, `alembic_version`, inventario y hashes de cada archivo, así como número de faltantes/excedentes.
5. Construir correspondencia de todos los documentos con ruta almacenada en BD: cada archivo referenciado debe existir, ser legible, tener la ruta confinada y coincidir con hash guardado cuando lo haya. Informar por tenant número de expedientes/documentos, archivos faltantes, huérfanos y duplicados; no asumir equivalencia conteo de filas = conteo de archivos (versiones y multipágina pueden diferir).
6. Con cuentas sintéticas, probar acceso autorizado al propio tenant y rechazo por otro tenant sobre un duplicado del servicio o fixtures aislados. No utilizar datos reales ni exponer documentos sensibles para demostrar RBAC.
7. Sobre una copia adicional de la DB restaurada, verificar `alembic upgrade 0039`, `downgrade -1` desde 0039 y `upgrade head` con el código **del commit de integración aprobado**; confirmar conteos/checkpoints y rollback. No tocar migraciones de la DB de staging original.
8. Probar reversión de aplicación en copia aislada y dejar registro: commit de retorno, copia necesaria, validaciones healthcheck, condiciones de abortar, responsable, duración y limpieza segura. Conservar logs de ejecución y su run ID, SHA exacto y checksums sin secretos.

## Criterios de aprobación

- Ambos respaldos pertenecen al mismo lote/ventana consistente y sus hashes verificados.
- Restore de BD y archivos en destinos efímeros sin alterar ningún origen, inventario consistente, sin referencias faltantes no explicadas, separación por tenant y RBAC con evidencia.
- Alembic y reversión comprobados en copia efímera.
- Informe firmado por operador autorizado, logs/URLs y plan de restauración validado.

## Herramientas y ejecución

El conector GitHub de esta sesión no expone `workflow_dispatch` ni SSH/VPS. Los workflows manuales existentes apuntan a respaldos históricos y **no realizan este ensayo coordinado**. Se requiere operador con acceso autorizado a staging, o un workflow nuevo explícitamente revisado y aprobado para entorno efímero; no se debe activar a ciegas en `main`.

**Decisión: gate S ABIERTO, I y D BLOQUEADOS.**
