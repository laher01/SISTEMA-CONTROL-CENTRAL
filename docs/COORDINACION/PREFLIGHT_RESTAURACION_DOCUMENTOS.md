# Preflight complementario — correspondencia DB restaurada y volumen documental

Estado: implementación de verificador **offline** (solo lectura). No integrado al workflow de despliegue; no sustituye backup ni prueba de restauración de volumen.

## Antecedente
`deploy/preflight-backup-restore-items.sh` valida un dump PostgreSQL y lo restaura temporalmente. Los bytes documentales residen en el volumen independiente `fact_central_staging_documentos` montado en `/data/documentos` para backend. El dump PostgreSQL **no incluye** esos archivos.

## Verificador incluido
`deploy/verify_document_volume.py` admite un manifiesto TSV por stdin con **tenant_id, ruta_storage, sha256** extraídos de la **copia restaurada**, no de la base viva. Con `--documentos /ruta/montada`, valida archivos, hash SHA-256 y contención de cada ruta bajo su tenant. El script no revela archivos ni modifica volúmenes y devuelve error si falta o no coincide cualquier fila.

Ejemplo únicamente para un entorno de prueba que ya dispone del manifiesto y un volumen restaurado AISLADO:

```sh
python3 deploy/verify_document_volume.py --documentos /ruta/aislada/documentos < manifiesto_restaurado.tsv
```

No ejecutar contra el volumen productivo como sustituto de respaldo. Para certificar restauración, restaurar primero una **copia documental aislada** en otro volumen, obtener el manifiesto de la DB restaurada y ejecutar allí. Verificar que el manifiesto incluya todos los documentos esperados; con cero filas el script termina correctamente, pero eso no certifica integridad de inventario.

## Requisitos bloqueantes pendientes para CI/CD
1. Definir herramienta de backup persistente de volumen documental, incluyendo snapshots consistentes y retención/ubicación externa cifrada.
2. Restaurar automáticamente en volumen nuevo, sin montar ni alterar el volumen productivo.
3. Exportar metadatos desde la base temporal restaurada y asegurar conteos completos; preservar nombres especiales con un protocolo de manifiesto que no permita tabs/nuevas líneas sin codificación.
4. Ejecutar este verificador contra la copia aislada y bloquear despliegue ante el primer error.
5. Probar migración 0037 y downgrade/reupgrade **solo** en base aislada, nunca sobre la productiva.
6. Obtener evidencia de ejecución en VPS antigua y comprobar recuperación de documentos, DB y configuración de forma conjunta.

## Coordinación
Infraestructura/respaldos es el módulo responsable. Seguridad SUPERADMIN/Issue #311 depende de estas verificaciones para su futura integración; no se incorporó ninguna modificación a PR #323, al workflow productivo o a la VPS.
