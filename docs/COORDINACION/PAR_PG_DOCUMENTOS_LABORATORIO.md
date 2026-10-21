# Coordinación PG + documentos — laboratorio aislado (PR en borrador)

**Estado:** prototipo de laboratorio. Nunca ejecutar en producción ni usar como
control de despliegue. Base: PR #333 (que a su vez depende de PR #328).

## Contrato de consistencia

El par lógico requiere ausencia de altas, cambios, eliminación y movimiento de
archivos durante **toda** la captura. `pg_dump` garantiza un snapshot SQL, **no**
uno entre SQL y archivos. La opción `--escrituras-detenidas` es una afirmación
del operador, **no prueba ni detiene escrituras**. Solo usar una copia offline
congelada junto con una base local de laboratorio de la misma generación.
La captura no certifica consistencia ni fiabilidad recuperable en producción.

## Alcance operativo

`deploy/backup_pair_isolated.py` restringe la conexión por `-h 127.0.0.1` y
acepta exclusivamente nombres `factcentral_fixture_*` de origen y
`factcentral_recovery_*` de restauración. **Ambas bases se crean previamente
en una instancia PostgreSQL LOCAL de laboratorio** y con usuario restringido.
No crea ni elimina bases ni incluye configuración de la VPS.

La entrada documental tiene que ser copia congelada y ajena al volumen Docker
productivo. Nunca usar contraseñas como argumentos de consola. Un operador
de laboratorio debe suministrar autenticación local por mecanismos de
PostgreSQL seguros (por ejemplo, `PGPASSFILE` local protegido).

### 1. Captura desde materiales de laboratorio congelados

```bash
python3 deploy/backup_pair_isolated.py backup \
  --db-fixture factcentral_fixture_prueba --usuario operador_laboratorio \
  --documentos-offline /laboratorio/instantanea_documentos \
  --destino-nuevo /laboratorio/nuevo_par \
  --escrituras-detenidas
```

Emite `postgres.dump`, `documentos.tar` y `pareja.json` con
SHA-256, tamaños y etiqueta explícita
`QUIESCENCIA_EXTERNA_NO_VERIFICADA`. La salida debe ser un directorio nuevo
y su acceso debe mantenerse privado. El archivo TAR **no está cifrado**.

### 2. Restauración y verificación aisladas

Crear previamente **una base local nueva y vacía** llamada
`factcentral_recovery_prueba`, con permisos restringidos. No usar bases
compartidas. Elegir un destino documental inexistente.

```bash
python3 deploy/backup_pair_isolated.py verify \
  --pareja /laboratorio/nuevo_par/pareja.json \
  --db-restaurada-vacia factcentral_recovery_prueba \
  --usuario operador_laboratorio \
  --documentos-destino-nuevo /laboratorio/restauracion_documentos
```

La herramienta:
1. Valida tamaño y SHA-256 de ambos artefactos.
2. Comprueba que la base destino no contenga tablas de usuario.
3. Restaura dump con `pg_restore --no-owner --no-acl --exit-on-error`,
   sin `--clean` ni `--create`.
4. Restaura TAR a destino nuevo con publicación sin sobrescritura de PR #333.
5. Extrae **solo de la base restaurada** el `count(*)` y las filas de
   `documentos(tenant_id,ruta_storage,sha256)`. Verifica coincidencia de
   recuento, UUID y formato canónico de almacenamiento.
6. Compara hashes de cada archivo usando el verificador de PR #328; cualquier
   ausencia, ruta fuera de tenant o diferencia detiene la comprobación.

**Importante:** el cotejo no prueba ausencia de archivos huérfanos en el TAR;
comprueba documentos referenciados por DB. Una verificación fallida puede dejar
una base restaurada parcialmente y un árbol de archivos; no reintentar sobre el
mismo destino. Proceder a limpieza manual **solo de recursos de laboratorio**.

## Pruebas y pendientes

Las pruebas unitarias simulan respuestas de `psql` y `pg_restore` para
confirmar rechazo de destinos con tablas, nombres fuera de laboratorio,
descuadres de recuento, rutas y huellas inválidas.

**Bloqueantes:** ejecutar integración con PostgreSQL real en ambiente aislado,
verificar permisos/roles y codificación `COPY`; obtener snapshot quiescente
comprobable; cifrado autenticado, custodia de claves, retención, copia externa,
resistencia a cortes, controles de cuotas y memoria, fsync y restauración
medida. Se requieren además controles de otros archivos que puedan existir
fuera de `documentos` (por ejemplo adjuntos de chat) antes de declarar
respaldo integral del SaaS. Nunca afirmar que CI prueba recuperación VPS.

Ninguna modificación a `main`, GitHub Actions, VPS o despliegue está prevista.
