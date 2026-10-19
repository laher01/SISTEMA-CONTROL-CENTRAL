# Cierre funcional — Contabilidad de Ítems (19/10/2026)

**Responsable:** módulo Contabilidad de Ítems. Este acta no audita ni desarrolla VPS, Actions, GitHub Rulesets, backups o despliegue.

## Candidata y compatibilidad
- PR #327, DRAFT: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/327
- HEAD validado `8dac6e39aa3f68e5452e70f23ebb6bbc89c3692b`, main base `e24599110f95b2f089fffd54ae013f827d3ae7ef`, behind=0, mergeable=true.
- Cambios confinados a rutas API, servicio UBL, servicio de reescaneo, página ContabilidadItems, tres archivos de tests y documentación del propio módulo. Sin modificaciones al workflow ni a infraestructura.
- No se copiaron migraciones obsoletas; se conservó la conciliación por moneda, RBAC RESPONSABLE y la extracción PDF/SCORPIO existente en main.

## Pruebas efectivas
- Workflow HEAD #327: backend, frontend, recepcion-documental-ci, roles-real-integration, roles-browser-isolated: **5/5 SUCCESS**.
- Log backend: **559 passed, 10 warnings in 126.12s**; `test_contabilidad_items_persistencia.py` 8 pruebas; `test_contabilidad_items_reescaneo.py` 15; `test_items_product_invoice_links.py` 1; `test_alembic_0034_integracion.py` 1 (PostgreSQL efímero).
- Cobertura de API/UI/servicios relevante: filtros (búsqueda/categoría/fechas/emisor/receptor), CSV consistente, vínculos factura→ítem y producto→facturas, validación de tenant y roles, exclusión de documentos retirados, persistencia idempotente, concurrencia, XML de reescaneo con hash/rutas/límites.
- No se ejecutaron pruebas locales adicionales en este cierre: se inspeccionaron archivos y logs de CI existentes. Sin fallos funcionales nuevos demostrados; no se modificó código.

## Criterios de aceptación funcional cuando el responsable correspondiente lo incorpore
1. En UI, filtrar por descripción/categoría/emisor/receptor y fechas; confirmar unidades y monedas sin agregaciones incompatibles.
2. Confirmar descarga CSV coincide con filtros autorizados.
3. Seleccionar producto y abrir sus facturas/expedientes vinculados sin atravesar roles ni tenants.
4. Repetir ingesta de mismo XML y procesamiento concurrente: no duplicar ítems; mantener contabilidad de origen.
5. Reescaneo paginado: verificar integridad hash, tenant, errores recuperables; nunca alterar originales fiscales.
6. Validar navegación y permisos de ADMINISTRADOR, SECRETARIA, GERENTE, RESPONSABLE, GESTOR y USUARIO, incluidos usuarios de dos empresas diferentes.
7. Constatar conciliación por moneda y exclusión de facturas observadas o documentos retirados según reglas de negocio.

## Entrega al proceso de integración (fuera de alcance)
- PR #327 tiene 0 reviews al cierre; requiere revisión/aprobación e integración autorizada por el responsable de I.
- Coordinación con 000 es dependencia externa, no un pendiente de desarrollo de Ítems. La VPS y despliegue D corresponden exclusivamente a su equipo/chat.
- Hasta ejecutar aceptación sobre versión real, estado: **CIERRE FUNCIONAL CANDIDATO, PENDIENTE DE INTEGRACIÓN Y ACEPTACIÓN EN SISTEMA**.

No merge, main, VPS ni deploy.
