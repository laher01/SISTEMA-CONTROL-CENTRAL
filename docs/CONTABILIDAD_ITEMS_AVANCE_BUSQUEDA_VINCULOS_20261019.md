# Contabilidad de Ítems — cierre parcial C, 19/10/2026

## Estado de origen comprobado
- PR #320 DRAFT, base rama de PR #186 `feat/contabilidad-items-auditoria-20261014`; HEAD inicial `13ff1754ba1ea59c0535cfe4c02d93116586ad8a`: **5/5 CI SUCCESS** (frontend, backend, recepción, roles real, roles navegador).
- PR #186: `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`, DRAFT.
- PR #281: `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`, DRAFT, reescaneo XML; no se modificó.
- PR #320 se mantiene aislado, sin actualizar base funcional ajena.

## Mejora desarrollada
- La búsqueda `buscar` de `GET /api/v1/contabilidad-items` ahora localiza tanto `ProductoItem.descripcion` como `LineaComprobanteItem.descripcion_original` mediante criterios parametrizados por SQLAlchemy, conservando límites por tenant, rol, fecha, emisor, receptor y estado.
- `GET /api/v1/contabilidad-items/exportar-csv` incorpora `buscar` y `categoria`, delegados al mismo resumen; evita exportar filas ajenas a los filtros usados en pantalla.
- `GET /api/v1/contabilidad-items/productos/{id}/facturas` ya desarrollado en PR #320 permite navegar a comprobantes/expedientes con límites por ámbito. La versión actual no incluye paginación por cursor ni búsqueda de alias no persistidos.
- Prueba `backend/tests/test_items_product_invoice_links.py` extendida a búsqueda por categoría/descripción y CSV filtrado con datos sintéticos de dos tenants.

## Evidencia y pendientes
- Commit código `5c8b242dffe08c7cca43d5f57c1290d8ce7d3f58`, test `135105efd159371a5c661349715eda2e3b090793`.
- CI del commit de pruebas aún debe comprobarse completo antes de certificar la ampliación.
- Pendiente mejorar UX de selección de emisor/receptor (actualmente exige UUID), validar diferencias reales entre nombre canónico y descripción original, pruebas de roles/estado, accesibilidad y paginación del detalle.
- No se ha hecho merge, deploy, migraciones ni cambios en main/VPS. Eliminación es responsabilidad exclusiva del PR #292; pedidos fuera del alcance.
