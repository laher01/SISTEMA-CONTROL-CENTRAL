# Procedimiento propuesto: recuperación conjunta aislada

**Estado:** desarrollo experimental sin uso productivo, sin acceso a VPS ni a bases reales.

## Secuencia controlada
1. Preparar una **captura consistente** de PostgreSQL y del volumen documental. Deben mantenerse detenidas/coordinadas las escrituras documentales y sus transacciones hasta capturar ambos recursos, o utilizar instantáneas con garantía equivalente. **No está implementado** el bloqueo coordinado: es un requisito previo obligatorio.
2. Documentar identificador único de captura, hora, hash de dump, hash de TAR y política de recuperación. Sin esa evidencia, no declarar el par consistente.
3. Restaurar el dump de PostgreSQL en una base NUEVA y aislada denominada `factcentral_restore_*`; restaurar el TAR mediante `deploy/document_archive_isolated.py restore` a un directorio nuevo, nunca al volumen original.
4. Ejecutar `python deploy/export_restored_manifest.py --dsn 'host=... dbname=factcentral_restore_prueba user=...' --salida /seguro/manifest.tsv`. Esta operación **solo lee** la base aislada. La salida es TSV sin encabezados. Anotar `REGISTROS_RESTAURADOS`.
5. Ejecutar `python deploy/check_restored_pair.py --manifiesto /seguro/manifest.tsv --documentos /aislado/documentos --esperados N`, con N igual al recuento de la etapa anterior.
6. Si hay cualquier diferencia, **bloquear integración/despliegue** e investigar documentos, tenants y hashes. No borrar respaldos o documentos originales.

## Limitaciones y requisitos abiertos
- NO hay captura real coordinada, backup o restore automático de Docker/PostgreSQL, cifrado, custodia externa, ni prueba de recuperación en VPS.
- Los nombres `factcentral_restore_*` son una salvaguarda adicional, pero no garantizan aislamiento de red ni evitan que una conexión mal configurada apunte a otro servidor. Requerir entorno físicamente/lógicamente aislado y credenciales solo lectura.
- El manifiesto y la lista de documentos deben corresponder al mismo snapshot; una igualdad de número/hash no prueba por sí sola el origen correcto del snapshot.
- El cotejo no comprueba todos los archivos sobrantes del volumen, y el esquema de documentos borrados requiere revisión de política legal.
- `export_restored_manifest.py` necesita `psycopg` disponible, un DSN seguro y una ubicación privada para el TSV; nunca registrar contraseñas.
- `document_archive_isolated.py` es experimental y mantiene los bloqueantes señalados en el PR #333.
