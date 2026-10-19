# Prototipo de recuperación documental aislada — PR de infraestructura

Este procedimiento es **offline y experimental**. Incluye SHA-256 por bloques, límites configurables mediante `--max-entradas` y `--max-bytes`, validación previa del árbol TAR y restauración privada publicada al finalizar. No lee credenciales, no se conecta a la VPS, no copia por sí mismo el volumen Docker productivo y no está conectado a Actions/deploy.

## Alcance de la prueba
1. Preparar una **instantánea documental estable**, previamente obtenida y montada en un directorio de pruebas; no utilizar el volumen productivo en vivo ni asumir consistencia mientras ocurren escrituras.
2. `python3 deploy/document_archive_isolated.py backup --origen /copia/estable --archivo /respaldo/nuevo.tar`. Conservar la huella SHA-256 indicada.
3. `python3 deploy/document_archive_isolated.py restore --archivo /respaldo/nuevo.tar --destino /copia/restaurada/NUEVA --sha256 HUELLA`. Rechaza sobrescribir un destino existente.
4. Restaurar **PostgreSQL en otra base aislada** mediante el procedimiento existente; extraer de ella el recuento y manifiesto completos de `documentos(tenant_id, ruta_storage, sha256)`.
5. Ejecutar `python3 deploy/verify_document_volume.py --documentos /copia/restaurada/NUEVA --esperados TOTAL_RESTAURADO < manifiesto.tsv`. El manifiesto debe proceder de la misma generación lógica del respaldo documental.

## Restricciones y bloqueantes
- El archivo tar no es snapshot atómico de datos en modificación. Faltan coordinación de escrituras, estrategia de consistencia entre DB y volumen, cifrado, retención y copia fuera de la VPS.
- No se automatiza todavía extracción de manifest/total PostgreSQL ni su codificación robusta para rutas especiales.
- No se ha ejecutado restauración real en VPS ni probado migración 0037/downgrade; esto exige autorización e infraestructura aislada.
- `verify_document_volume.py` acepta documentos cuando sus hashes coinciden con el manifiesto suministrado, pero un manifiesto incorrecto/corrupto que comparta recuento requiere cotejo de origen independiente.
- El archivo tar se crea sin cifrar: almacenar solo en ubicación segura, acceso restringido; no usar con documentos reales hasta definir cifrado y custodia.
- Faltan pruebas de archivos extremadamente grandes, cuotas y cortes por falta de espacio; no se debe conectar al gate de despliegue hasta completar controles.

La integración de este PR y PR #328 debe revisarse en infraestructura; PR #323 tiene objetivo distinto (sesiones tenant). Nunca fusionar el PR temporal #331.

## Condiciones adicionales de seguridad
- La publicación por renombrado funciona cuando el directorio temporal y el destino comparten sistema de archivos. No elimina todos los riesgos de concurrencia ni prueba recuperación tras apagado.
- La validación con SHA-256 no autentica el origen: debe protegerse la huella mediante custodia independiente y cifrar los respaldos reales.
- Continúa **BLOQUEANTE** la consistencia temporal y recuperación conjunta PostgreSQL/documentos; no usar este prototipo como gate de despliegue.

## Seguridad de publicación y recursos (prototipo)
- Publicación usa `renameat2(RENAME_NOREPLACE)` de Linux; falla de forma cerrada si falta soporte y **nunca** acepta sustituir el directorio de destino.
- TAR limitado a 12 GiB y cuota de entradas/bytes declarados; comprobación previa de espacio libre con margen de 1 MiB. No garantiza espacio durante escrituras simultáneas ni limita exhaustivamente memoria de metadatos.
- Respaldo nuevo con permisos 0600 y eliminación del archivo final parcial cuando falla la copia.
- Faltan pruebas de truncamiento específico e interrupciones de E/S sobre archivos de múltiples GiB; el preflight de producción no utiliza esta herramienta.
- **Bloqueantes:** captura consistente PostgreSQL/documentos, cifrado, backups externos, recuperación comprobada, controles de acceso y retención.
