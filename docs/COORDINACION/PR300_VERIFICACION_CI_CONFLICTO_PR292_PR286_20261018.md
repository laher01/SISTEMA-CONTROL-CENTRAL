# Gate S — Cierre de verificación CI y contraste #292/#286 (18/10/2026)

## Evidencia CI
- PR #300 SHA inicial `0602deb2a70f14c37541fb0a872e345093c6ef72`: CI **4/4 SUCCESS** (backend run 39194619608, recepción 39194619644, roles 39194619624, guardrails 39194619633).
- Commit de tests `6fc74f040ead33d8855f8af49a8d5e3c7007f511`: **4/4 SUCCESS** (backend 39194560865, recepción 39194560878, roles 39194560882, guardrails 39194560887).
- Log Backend del SHA `0602deb2`: `tests/test_gate_s_two_tenant_http.py ..` y `508 passed, 10 warnings in 92.67s`. Los casos comprueban restauración simulada por cambio de `deleted_at`, deduplicación línea UBL, FACT más documentos GRE/VCHR sin duplicación de total y auditoría `OBSERVADA` segregada en conciliación. **No cubren el endpoint real de restauración.**

## HEAD funcionales cotejados
- #292 `454d11ee4a60b8858031fca0b429c4dedf67d0b8`, DRAFT.
- #286 `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`, DRAFT.
- #186 `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`; #281 `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`; #211 `11c8c9b4669ac4878d8aecfefd542c336e9014e2`; #212 `14fb6583825c7779871291c96197d3b51da16a00`.

## Contrato incompatible CONFIRMADO por archivos completos
En `backend/app/api/routes/documentos.py` de #292, `retirar_documentos_lote` llama a `eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)`, y `eliminar_documento` acepta esos seis argumentos, hace **retirada lógica** `deleted_at=ahora()`, conserva archivos y registra auditoría. 
En #286, `eliminar_documento` recibe además `almacen` antes de `documento_id`, y aplica **eliminación física controlada** para documentos no asignados y flujo integral específico. Combinar ambos sin adaptación produce incompatibilidad de firma y, peor, riesgo de invocar una baja definitiva desde la retirada masiva. **No resolver cambiando solo la firma.**
En #292, `restaurar_documento` es individual y rechaza si el expediente vinculado está retirado (409). El documento `PR292_DEPENDENCIAS_RESTAURACION_EXPEDIENTES_20261018.md` declara que todavía **no existe restauración integral de expedientes**. La retirada integral deja GRE y voucher ligados; `PagoERP.voucher_documento_id` persiste aunque el documento quede retirado.

## Bloqueantes de integración
1. Acordar con propietarios operaciones distintas para retiro recuperable y eliminación física; RBAC por operación, ámbito, tenant y propietario; SUPERADMIN no accede por defecto a APIs operativas.
2. Definir restauración integral de expediente, discriminando documentos retirados previamente y los retirados por cascada; validación original SHA, conflictos de identidad y rollback atómico.
3. Determinar conducta de GRE y pagos/vouchers al retirar/restaurar; evitar romper referencias históricas, ocultar pagos válidos o alterar importes.
4. Probar incompatibilidad #286/#292 en árbol candidato aislado y entorno descartable, **sin fusionar sus PR ni main**. No afirmar integración runtime aprobada mientras esté abierta.
5. Ensayar Alembic y operaciones FS/DB con autorización independiente, solo DB de pruebas.

Gate S **OPEN**. PR #300 DRAFT. No merge, main, VPS ni despliegue.
