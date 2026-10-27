# Candidato conjunto OCR ingreso + MISD sobre main 703d20c4

## Alcance

- Base: `703d20c4c2c194160f5838607a267fc14382806b`.
- Ingreso fiscal: los tres archivos de PR #405, HEAD `e93a27d72efa34d7b08ff3d88d55c0e60554b6bc`.
- OCR-Totales: ya incorporado en la base por PR #403; no reaplicar PR #339 ni #397.
- MISD: cambios de PR #292, HEAD de origen `c2c686011e44831bb6487263c3e723e9e171097d`, corregidos en esta rama.

## Correcciones de seguridad y mantenimiento

- `ELIMINAR_REGISTROS` respeta la configuración por tenant para roles delegados; fila ausente o deshabilitada deniega.
- La vista previa y la retirada aplican la misma ventana de corrección; una selección vencida informa `REQUIERE_MISD`.
- Mantenimiento bloquea antes de mutar si un expediente seleccionado tiene historial de solicitud MISD; conserva la evidencia auditable y evita el error de FK.
- Las rutas de solicitud, listado, aprobación y ejecución MISD se habilitan para RESPONSABLE; el ámbito jerárquico y el permiso del tenant se siguen validando en el backend.
- La creación de solicitud y limpieza bloquean los expedientes seleccionados para evitar carreras con la FK.

## Migraciones y límites de coordinación

- La base contiene la revisión `0041`; este candidato MISD conserva `0042` con `down_revision = "0041"`.
- PR #313 de Etapa 7 también declara `revision = "0042"`. Etapa 7 pertenece a otro chat: sus archivos no se modifican aquí.
- Antes de integrar ambos cambios, el responsable de Etapa 7 debe coordinar una revisión CMS nueva, por ejemplo `0043` descendiente de MISD `0042`, y ejecutar Alembic desde base y en restauración aislada. No combinar dos revisiones con el mismo ID.
- No fusionar ni desplegar este candidato. No cambia fórmulas, pagos, expedientes históricos ni archivos físicos de documentos.

## Validación

- CI conjunta queda pendiente de ejecución sobre esta rama tras crear el PR borrador.
- La CI individual de PR #405 no sustituye la CI conjunta con MISD.
- Deben pasar backend con PostgreSQL, frontend, roles reales, roles de navegador, recepción documental, migraciones, guardrails de coordinación y gate común.
