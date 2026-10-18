# PR264 — Evidencia de contratos OCR/NEXUS y seguridad S (2026-10-18)

## Estado validado
Commit base `5f14b86e979cc8211fc9346a2b4da4fe8528a237`: seis workflows SUCCESS, incluyendo auditoría offline, PostgreSQL 16/17, backend, roles, recepción y coordinación. PR #264 draft.

## Contratos observados en main (revisión de código)
- `backend/app/services/ingesta.py` contempla `ComprobanteYaRegistrado` y busca documentos mediante `Documento.tenant_id == tenant_id` y SHA-256; las funciones `vincular_documento` y otras validan pertenencia del expediente al tenant. Es evidencia de filtros de aplicación, **no prueba por sí sola de aislamiento bajo concurrencia ni de políticas RLS**.
- `backend/app/services/automatizacion_documental.py` registra `EXTRACCION_DOCUMENTAL_VALIDADA_AUTOMATICAMENTE`, usa `documento.tenant_id` para consultas y escrituras, y rechaza otra FACT en el expediente mediante `ComprobanteYaRegistrado`. Queda por probar colisiones fiscales simultáneas en PostgreSQL real bajo transacciones concurrentes.
- La búsqueda de código para `storage.file.available` solo devolvió documentación `docs/CORE/08_CORE_INTEGRATION_CONTRACTS.md` y `docs/INGESTA_IMAGENES_LOTES_OCR_V1.md`; no se ha acreditado aquí un emisor/consumidor runtime real. Esta búsqueda no demuestra inexistencia absoluta en todos los componentes.
- PR #277 OCR fusionado en main. PR #275 v2 draft tiene los 14 blobs de código/documentación iguales a main; evitar duplicar sus cambios.

## Matriz obligatoria en rama OCR/NEXUS separada
| Caso | Verificación requerida | Evidencia actual |
|---|---|---|
| Carga idéntica dos veces | resultado idempotente y cero doble efecto económico | filtros tenant + SHA en ingesta; **faltan pruebas E2E** |
| Dos facturas mismo identificador fiscal concurrentes | restricción única transaccional; un expediente | excepción `ComprobanteYaRegistrado`; **falta carrera concurrente real** |
| Tenant A y B con mismo RUC/serie | no acceso cruzado ni asociación | filtros en consultas; **faltan tests de dos sesiones/autorizaciones** |
| OCR incompleto o contradictorio | `REVIEW_REQUIRED` o `CONFLICT_REVIEW`, sin cobro automático | contrato y política, **falta prueba E2E** |
| Event replay OCR→NEXUS | `event_id` idempotente, tenant y versión obligatorios | contrato documentado, **emisión/consumo no verificados** |
| GRE/voucher/OC | solo vínculos autorizados, sin factura/economía inventada | contrato OCR Core, **falta E2E** |
| Backups pareados DB+archivos | SHA, rollback, RBAC, Alembic en staging aislado | pruebas sintéticas, **staging no ejecutado** |

## Requisitos de finalización
No habilitar gate S sin prueba pareada en staging auténticamente aislado, evidencia de integridad y revisión independiente. I y D permanecen bloqueadas. Mantener PR264 en borrador y PR275/277/208/237/249 sin cambios. Prohibido conectar VPS, fusionar o desplegar.
