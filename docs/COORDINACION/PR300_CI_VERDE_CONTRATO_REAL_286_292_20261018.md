# PR #300 — Resultado estático contra SHA reales y CI (18/10/2026)

## CI verificado
HEAD de código `e2cb40dcb23e48ef01e08fcdfc5235537d6da0a4`:
- backend — run `39170950658`: SUCCESS
- recepcion-documental-ci — run `39170950640`: SUCCESS
- roles-real-integration — run `39170950665`: SUCCESS
- coordination-guardrails — run `39170950653`: SUCCESS

**4/4 verde para ese SHA**, no valida ramas funcionales combinadas.

## Inspección estática directa (archivos completos vía GitHub fetch_file, sin checkout ni merge)
- #286 `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`: `backend/app/api/routes/documentos.py`, firma:
  `eliminar_documento(session, settings, hoy, tenant_id, auth, almacen, documento_id)`. Siete argumentos posicionales, con `almacen` como sexto.
- #292 `61a3a18aa071a2fb1a638ccf2285d3451db1eeba`: mismo archivo; `retirar_documentos_lote` invoca `eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)`: seis argumentos, sin `almacen`.
- **Conclusión:** diferencia comprobada de firma/llamada. Si se reusara sin adaptación la función de #286 en el contexto del lote de #292, la llamada resultaría inválida. Más grave, la función de #286 puede realizar eliminación física definitiva, mientras la retirada de #292 está diseñada para ser recuperable. Un simple ajuste de parámetro NO resuelve la incompatibilidad semántica.
- #186 `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`: existe el servicio `contabilidad_items_ubl.py` para persistencia idempotente por documento/línea.
- #281 `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`: incluye `with_for_update()` para Tenant en el mismo servicio; requiere revisión conjunta de los contratos de bloqueo con #286.

La inspección fue ejecutada mediante consulta de archivos a GitHub y comparación directa de firma/llamada; **el script CLI de `scripts/gate_s_contract_dryrun.py` no se ejecutó con checkout local que contenga estos SHA**. Sus pruebas sintéticas sí están cubiertas por CI verde, pero ello no acredita ejecución CLI real.

## Decisión de coordinación
1. Mantener implementación runtime de #286 al frente de eliminación; #292 al frente de papelera/restauración.
2. Resolver firma y especialmente semántica por endpoints y capacidades separadas; prohibir que `retirar_lote` invoque eliminación definitiva.
3. Verificar transiciones con FACT+GRE+voucher+ítems; pagos, líneas, archivos, huellas, permisos y auditoría sin residuos.
4. Ejecutar plan del documento `GATE_S_PLAN_E2E_SINTETICO_FACT_GRE_VCHR_ITEMS_RESTAURACION_20261018.md` en rama y PostgreSQL desechables solo cuando los propietarios hayan acordado el contrato.
5. Migraciones `0024/0035/0041`: metadatos documentados, **no se corrió Alembic**; comprobar grafo y compatibilidad en entorno descartable.

**Gate S OPEN.** PR DRAFT. No modifica main, ramas funcionales, VPS, producción, migraciones o despliegue.
