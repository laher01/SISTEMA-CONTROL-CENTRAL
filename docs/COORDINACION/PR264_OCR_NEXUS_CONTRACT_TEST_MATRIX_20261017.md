# PR264 — matriz contractual OCR → NEXUS y seguridad de recuperación

Fecha 2026-10-17. No hay cambios a runtime OCR/NEXUS; se restringe a contratos, pruebas sintéticas y CI aislado.

## Evidencia de partida
- PR264 commit `f2d693f056b136e357796821134b6f3b35c7e75e`: seis workflows SUCCESS.
- PR #277 OCR fusionado; #275 OCR DRAFT: los 14 blobs tocados son idénticos entre #275 y main `75e84c5d69ae1662d99e1ef671898586e2157f15`, ver `PR264_OCR_TREE_IDENTICAL_275_MAIN_GATE_20261017.md`.
- OCR integrado en main expone `POST /api/v1/documentos/lote-imagenes` para 1-10 imágenes individuales, no representa aún contrato completo de agrupación multi-página ni procesamiento de ZIP/RAR.

## Contratos mínimos propuestos para pruebas, NO endpoints ya implementados
| Interfaz | Precondición | Identidad/idempotencia | Caso de prueba requerido |
|---|---|---|---|
| Storage → OCR | `storage.file.available` confirmado | `tenant_id + file_id + version` | evento repetido no duplica documento |
| OCR → clasificador | evidencia y confianza por campo | `tenant_id + documento_id + extraction_version` | valores contradictorios a revisión |
| Clasificador → expediente | tipo y identidad fiscal verificada | `tenant_id + emisor + tipo + serie + correlativo` y receptor validado | dos subidas simultáneas crean un solo efecto económico |
| Documento auxiliar → expediente | relación probada / permisos | `tenant_id + document_id + expediente_id` | GRE/voucher no crea expediente fiscal sin factura |
| Expediente → NEXUS | evento auditable y versionado | `event_id + tenant_id + aggregate_id` | replay idempotente; acciones reversibles y RBAC |

## Matriz de pruebas obligatorias en futura rama OCR-NEXUS
1. Documento idéntico: SHA256 reingresado no duplica almacenado ni sumatorias.
2. Nueva fotografía con misma identidad fiscal: rechazo de expediente duplicado; decisión explícita sobre conservar solo evidencia auditada.
3. Identidad igual, importe/receptor divergente: `CONFLICT_REVIEW`; sin efecto económico.
4. Imágenes multipágina fuera de orden: no asumir que una foto representa una factura entera.
5. Dos tenants con RUC o correlativo idéntico: ningún cruce de datos, expediente, evento o deduplicación.
6. Reintento tras interrupción y replay: un solo `aggregate_id` final, auditoría de intentos.
7. Usuario sin permiso: RBAC deniega confirmar, vincular o modificar estado.
8. Factura, RHE, GRE remitente/transportista, voucher, cotización, OC, PDF escaneado, ZIP sospechoso y RAR no habilitado: verificación de tipo, seguridad y límites.
9. NEXUS consumidor: jamás debe ejecutar pagos, eliminación, envíos tributarios u otros cambios irreversibles mediante OCR no confirmado.
10. Coexistencia de versiones: comparar cambios del schema de Alembic y confirmar que restauración DB + documentos corresponde al mismo lote.

## Pruebas añadidas a seguridad del PR264
`deploy/test_recovery_pair_audit.py`: rechaza sustitución de un documento del tenant A por bytes del tenant B aunque tengan igual tamaño; rechaza reasignación de ruta de tenant aun cuando los bytes y SHA sean idénticos. Estas pruebas validan **integridad del manifiesto**, no autorización multi-tenant en API ni la identidad jurídica del contenido.

## Condiciones para FINALIZAR
No fusionar ni desplegar. Gate S sigue OPEN hasta validación de rollback de staging realmente aislado y revisión independiente. Gate I/D bloqueados. PR264 draft, no acceso a VPS, main ni PR ajenos.
