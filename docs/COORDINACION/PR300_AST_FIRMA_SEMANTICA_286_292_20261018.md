# Gate S — Evidencia de incompatibilidad detectada por AST (18/10/2026)

## Estado base comprobado
PR #300 HEAD previo `968ecea94917c9334059c2b80126153f1beb871f`: cuatro workflows SUCCESS. PR #292 **se actualizó** al HEAD `39722e2f6ef633f49c2e3f7183f521e8f832646d` durante esta revisión; #286 permanece en `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`. Ambos DRAFT.

## Evidencia fuente comprobada
- #292 `backend/app/api/routes/documentos.py`: `retirar_documentos_lote` pasa 6 argumentos posicionales a `eliminar_documento`; esta función escribe `documento.deleted_at=ahora()` (retirada lógica).
- #286 mismo archivo: `eliminar_documento` acepta 7 parámetros, incluido `almacen`, y llama `bloquear_tenant_documental`; su lógica es distinta, de eliminación controlada.
- Por tanto, conservar la llamada de #292 y sustituir la definición con la de #286 rompe la firma; y hacer coincidir las firmas **no autoriza** sustituir retirada recuperable por eliminación física.

## Pruebas añadidas a #300
- `scripts/gate_s_contract_dryrun.py` incorpora `lifecycle_semantics` para comprobar mediante AST: invocación por lote, cardinalidad posicional, presencia de parámetro de almacenamiento, escritura `deleted_at`, bloqueo, colisión de nombre y riesgo semántico.
- `backend/tests/test_gate_s_lifecycle_semantic_collision.py`: dos pruebas con fuentes sintéticas. Caso 1 exige detectar tanto firma como semántica incompatibles; caso 2 confirma que igualar parámetros no elimina el bloqueo semántico.
- El CLI del analizador acepta SHA de cada PR para ejecutar revisión local de fuentes con `git show`, sin checkout ni merge. **No se ha ejecutado CLI contra los SHA reales en esta sesión**; la comprobación de fuentes reales fue lectura de GitHub. Prueba unitaria CI sintética pendiente de estado final del nuevo HEAD.

## Criterios de desbloqueo
1. Operaciones explícitas independientes: `retirar_documento` (soft, reversible) y `eliminar_documento_definitivamente` (irreversible y autorizada); lote llama solamente a soft.
2. Aprobación de propietarios de #286 y #292. No cambiar silenciosamente semántica del DELETE existente.
3. RBAC por acción, tenant y propietario; los indicadores de capacidades no sustituyen validación dentro de la transacción.
4. Tests combinados en árbol aislado: restauración mismo ID, GRE/voucher/pagos, archivo SHA, sumatorias, rollback FS/DB, concurrente y colisión de reingesta.
5. Mantener Gate S OPEN y no fusionar mientras haya incompatibilidad o pruebas críticas sin ejecutar.

No se modificaron ramas ajenas, main, VPS ni producción.
