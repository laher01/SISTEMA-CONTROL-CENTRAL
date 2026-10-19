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

## Verificación comando T — SHA 2665855f6c62bb501a3cdd42601d0aed65613a4f
- GitHub PR #325 permanece DRAFT, HEAD coincidente con este SHA antes de esta actualización documental.
- Backend run `39211509640`: ejecutó con éxito `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`; `uv run pytest` estaba **en ejecución** durante la comprobación.
- Recepción run `39211509807` y Roles Real run `39211509698`: **en ejecución**; no hay resultados concluyentes ni prueba que corregir por ahora.
- El servicio CI Backend levanta contenedores de prueba, pero no incluye un paso explícito de `alembic upgrade head` en su lista de pasos. Por tanto **no se ha verificado migración Alembic completa de la candidata** mediante este workflow.
- Se intentó consultar logs pytest con GitHub durante la ejecución; API temporalmente respondió `404 BlobNotFound`. No se afirma resultado pytest.
- No se hicieron cambios en Python/TSX ni acciones de fusión, VPS o producción. El cierre exige revisar el resultado final del CI y ejecutar/constatar Alembic en DB efímera antes de autorizar integración.

## T — Pruebas verificadas después de finalizar CI de SHA 2665855f
- Workflows `backend` run 39211509640, `recepcion-documental-ci` run 39211509807 y `roles-real-integration` run 39211509698: **SUCCESS 3/3**.
- Log pytest Backend job 117925736887: **406 passed, 8 warnings in 93.77s**.
- Log incluye `tests/test_contabilidad_items_persistencia.py ...... ` (6 aprobadas), `tests/test_contabilidad_items_reescaneo.py ...............` (15 aprobadas) y `tests/test_items_product_invoice_links.py .` (1 aprobada). La prueba de concurrencia PostgreSQL está entre las seis de persistencia, sin omisiones en esa batería.
- **Alembic sí quedó verificado en CI**: el log muestra `tests/test_alembic_0034_integracion.py .`; el test crea una DB temporal `fc_migration_check_*`, ejecuta `command.upgrade(config, "0034")` y después `command.upgrade(config, "head")`, comprueba revisión 0035 y destruye la base al terminar. No requiere acceso a VPS. Esto corrige la cautela anterior que decía que faltaba comprobar Alembic: no existía un paso separado del workflow, pero sí la prueba de migración completa dentro de pytest.
- HEAD documental de entrada `95bff9e3b2ef443f3854fa585e3dfcefbffd6368`: sus tres workflows seguían en ejecución durante esta consulta; la evidencia exitosa del commit de código es válida, sin inferir estados del nuevo HEAD.
- No se encontraron fallos nuevos que justifiquen corregir código; no tocar ramas fuente ni producción.
