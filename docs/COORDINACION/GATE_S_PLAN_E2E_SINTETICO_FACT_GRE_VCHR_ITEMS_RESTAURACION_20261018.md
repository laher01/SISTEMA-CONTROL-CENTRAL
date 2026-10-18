# Gate S — Plan transaccional sintético FACT/GRE/VCHR/ítems y retirada/restauración

**Fecha:** 18/10/2026. **Solo planificación**; no se han realizado pruebas E2E de ramas combinadas ni migraciones reales.

## Insumos bajo evaluación
- #286 eliminación y reingesta, HEAD `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`
- #292 papelera/restauración, HEAD observado `61a3a18aa071a2fb1a638ccf2285d3451db1eeba` (volver a verificar antes del ensayo)
- #186 ítems, HEAD `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`
- #281 reescaneo UBL, HEAD `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`
- #289 NEXUS casos OCR y #102 Responsable implican migraciones separadas; no se usará su código sin verificación de línea Alembic.

## Requisitos de aislamiento
Base PostgreSQL descartable, carpeta temporal de documentos, datos creados sintéticamente, tenants A/B y sesiones autenticadas separadas. Ningún secreto, archivo real, VPS, ni tablas productivas. El ensayo de combinación debe quedar en rama experimental independiente **después** del acuerdo de los dueños #286/#292 sobre firmas/semántica. No resolver divergencias de módulos funcionales desde el PR #300.

## Casos y afirmaciones comprobables
| Paso | Operación | Aserción |
|---|---|---|
| 1 | Crear tenant A y tenant B; roles Gestor, Responsable, Administrador | Todo registro lleva tenant correcto y actor con permiso explícito |
| 2 | Registrar FACT UBL sintética en A con dos líneas (unidades/monedas conocidas) | Exactamente dos líneas, una factura y un expediente |
| 3 | Vincular GRE y voucher a FACT | Referencias válidas, cero doble contabilización de importe |
| 4 | Consultar detalle y consolidados por API | Sumas coinciden con la factura, no con número de documentos |
| 5 | Retirar documento/lote recuperable | Original persiste, huella no muta, queda invisible en sumas activas |
| 6 | Restaurar tras retirar | Recupera el mismo ID original y líneas sin duplicarlas |
| 7 | Intentar eliminar FACT con GRE/voucher/pago referenciado | Rechazo atómico (409 o especificado), ningún huérfano |
| 8 | Eliminar definitivamente un caso **permitido y sin dependencias** | Diario y archivo/DB se sincronizan; auditoría no se pierde |
| 9 | Reingesta del mismo hash tras eliminación autorizada | Sin “fantasma” que bloquee alta, sin conteos/importe doble |
| 10 | Dos sesiones: reingesta y retirada del mismo hash | Transacciones serializadas o fallo seguro, jamás contenido inconsistente |
| 11 | Corte simulado entre renombrado de original y COMMIT | Reconciliación idempotente tras rollback, sin perder original |
| 12 | Intentos de tenant B y rol no autorizado | Denegación y ningún cambio en A |
| 13 | Reprocesar ítems UBL simultáneamente | Un ítem por (tenant, documento, numero_linea) y catálogo aislado |
| 14 | Probar pending_approval | Excluye montos no aprobados, conserva evidencia histórica |

## Condiciones previas del Gate
1. Reconciliar `retirar_documentos_lote -> eliminar_documento` con firma y **efecto no destructivo**.
2. Alinear `GET /capacidades` con la autorización efectiva de cada endpoint y tenant.
3. Resolver coexistencia de #286/#292/#186/#281 en rama desechable; comprobar diff real, sin importar código automáticamente.
4. Ejecutar `alembic heads`, `history`, `upgrade head` y prueba de downgrade únicamente sobre entorno efímero. Migraciones 0024→0023, 0035→0034 y 0041→0040 se validan contra archivos reales del árbol combinado.
5. Ejecutar CI con SHA de ese árbol, conservar resultados por workflow y recuentos SQL de pruebas. No extrapolar éxito aislado a integración conjunta.

## Estado del PR #300
HEAD inicial `dabb7d12313782b6a04a745d94995b922cbdb2e6`: Roles + Guardrails SUCCESS, Backend y Recepción fallaron en Ruff E501 por una línea larga de `test_gate_s_contract_dryrun.py`.
Corrección limitada a prueba sintética: `08caff123dce83b7fb020794b282ac0afc0c977f`. Reconsultar CI de ese SHA antes de declarar éxito.

**No se ha ejecutado el ensayo transaccional de esta tabla. Gate S OPEN.**
