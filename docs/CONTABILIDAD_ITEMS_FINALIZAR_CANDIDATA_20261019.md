# FACT CENTRAL — FINALIZAR Contabilidad de Ítems | Candidata aislada 19/10/2026

## Fuentes realmente verificadas
- PR #186 núcleo Ítems DRAFT HEAD `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`, base main, actualmente GitHub `mergeable=false`.
- PR #320 filtros + enlaces Ítems DRAFT HEAD `969911b0712ec628d5dc408bc749895d9f25a013`, base rama #186, `mergeable=true`, CI **5/5 SUCCESS** (Backend, Frontend, Recepción, Roles Real, Roles Browser).
- PR #281 reescaneo XML DRAFT HEAD `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`, base main, `mergeable=false`.
- PR #325 DRAFT candidato: branch `test/items-finalizacion-candidata-20261019`, base rama #320, HEAD fuente `76e475df7fbd52f97260a08c8c72337eecb46a67`.

## Composición exacta del candidato
El punto de partida en GitHub fue el HEAD probado de PR #320, que contiene el núcleo del PR #186 por ascendencia. Se trasladaron **solo a la rama candidata**, sin cambiar ninguna rama propietaria, los cuatro archivos cambiados por PR #281:
1. `backend/app/services/contabilidad_items_ubl.py` — bloqueo PostgreSQL por tenant y documento activo del mismo tenant.
2. `backend/app/services/contabilidad_items_reescaneo.py` — vista previa y proceso paginado con validación de ruta, hash, longitud e idempotencia.
3. `backend/tests/test_contabilidad_items_reescaneo.py` — pruebas sintéticas de reescaneo y aislamiento.
4. `backend/tests/test_contabilidad_items_persistencia.py` — pruebas adicionales multitenant, documento retirado/inexistente y concurrencia.

No hay implementación ni cambios sobre eliminación (#292), pedidos, migraciones ni interfaces ajenas.

## CI, pruebas y límites
- El PR #325 desencadenó workflows `backend` run `39211390668`, `roles-real-integration` run `39211390648`, `recepcion-documental-ci` run `39211390706`. **Iniciados, no finalizados en el momento del registro.**
- El CI verde del PR #320 certifica su propia rama, no la composición #320+#281.
- No se corrió una migración Alembic completa sobre DB efímera de esta candidata, ni pruebas de restauración o despliegue; no afirmar lo contrario.
- `mergeable=false` en #186 y #281 exige análisis de diferencias contra main/protecciones antes de autorizar integración. La candidata #325 no elimina estos bloqueos.
- Los tests de ítems usan archivos y base de datos de CI; las pruebas de reescaneo requieren almacenamiento temporal y PostgreSQL aislado.

## Siguiente etapa crítica
Corregir únicamente fallos reproducibles de candidata; comprobar resultados CI por SHA, evidencia pytest de reescaneo, aislamiento y concurrencia. Reconciliar con propietarios de #186/#281 antes de definir orden de integración. Integración a main requiere comando I autorizado; despliegue VPS requiere D y recuperación comprobada.

**No merge, no main, no VPS, no migraciones productivas, no deploy.**
