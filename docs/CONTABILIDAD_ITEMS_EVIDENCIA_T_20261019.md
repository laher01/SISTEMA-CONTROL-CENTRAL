# PR #320 — evidencia de pruebas T (19/10/2026)

## Estado inicial verificado
- PR #320 DRAFT HEAD `ded53dd5147522f035d131bd6c5519ba0fe6bbf3`, basado en PR #186.
- Workflows: Frontend, Roles Browser y Roles Real SUCCESS; Backend (run `39207883284`) y Recepción (run `39207883415`) FAILURE.
- Ambos pytest reportaron `1 failed, 385 passed, 8 warnings`. Único error en `test_search_and_linked_invoices_are_tenant_scoped`: `AttributeError: 'Query' object has no attribute 'strip'`; causado por pasar defaults FastAPI `Query` como valores de llamada Python interna a `resumen`.

## Correcciones y cobertura nueva
- Commit `0044db561636a4a0bc71072f1a225ff29288b855`: parámetros opcionales `buscar` / `categoria` usan `Annotated[...,Query(max_length=...)] = None`; se preservan validación HTTP y llamadas internas.
- Commit `ba84770b62c0890fb8c95a469065688662657142`: pruebas HTTP extra de fechas invertidas (422), rol SUPERADMIN denegado y filtro de emisor externo.
- Commit `cb2e158ad36b1ecd43412f847ecfa2d8ab1c38f6`: filtro de emisor externo usa ID real de empresa ajena (no ID de tenant).
- Permanecen en la prueba: búsqueda de descripción y categoría, CSV filtrado, aislamiento tenant, vínculo ítem→factura y exclusión de archivo retirado.
- La ejecución CI del último commit estaba **en curso** al redactar. No atribuir éxitos por inferencia.

## Límite de alcance
Solo archivos de Contabilidad de Ítems y pruebas del módulo. Sin modificaciones #186, #281, #292, #300, main, VPS, migraciones reales, merge o deploy. El contrato de reescaneo #281 requiere evaluación aislada posterior antes de integrar.


## Nueva iteración T — verificación y reparación del CSV
- HEAD de entrada `84036ae9e5d513ee06accae8e74f372f88bf81f2`, DRAFT: Frontend SUCCESS (run 39208486465), Roles Browser SUCCESS (39208486305), Roles Real SUCCESS (39208486268), Backend FAILURE (39208486415), Recepción FAILURE (39208486490).
- Evidencia de ambos logs pytest: `1 failed, 385 passed, 8 warnings`. Único fallo `tests/test_items_product_invoice_links.py::test_search_and_linked_invoices_are_tenant_scoped`: CSV con `buscar=anchoveta` contenía `Pota congelada`, porque `exportar_csv` recibía los parámetros pero no los transmitía a `resumen`.
- Corrección funcional limitada a Ítems: SHA `745fc5ab1b3d227e793b5413fcfa368a645f8090`; `exportar_csv` ahora envía `buscar=buscar` y `categoria=categoria` a `resumen`.
- Workflows de ese SHA: Frontend confirmado SUCCESS; otros inicialmente en curso. No inferir cierre general antes de inspeccionar los cinco resultados del commit.
- Las pruebas continúan usando PostgreSQL aislado, XML y empresas sintéticas; no hay datos productivos ni intervención sobre módulos externos.

Gate S sin modificación. PR #320 DRAFT. No merge, main, VPS ni deploy.
