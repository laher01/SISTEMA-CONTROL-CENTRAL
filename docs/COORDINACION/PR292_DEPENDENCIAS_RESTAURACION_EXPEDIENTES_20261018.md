# PR #292 — análisis de restauración de expedientes y referencias

Auditoría de código (rama `feat/document-retention-role-actions-20261018`). Este documento **no autoriza eliminar físicamente datos**.

## Comportamiento confirmado

- `DELETE /api/v1/expedientes/{id}` marca `Expediente.deleted_at` y marca como retirados todos sus `Documento` activos, registra eventos individuales y de expediente, y conserva los originales.
- `POST /api/v1/documentos/{id}/restaurar` exige expediente activo; rechaza documento asociado a expediente retirado mediante HTTP 409. Por tanto **no existe aún una restauración integral del expediente**.
- `actualizar_expediente` y `tipos_presentes` calculan documentos activos (`deleted_at IS NULL`) y sincronizan alertas. Retirada y restauración individual llaman al recálculo del expediente activo.
- `ReferenciaGRE.documento_id` referencia `Documento.id` y puede referenciar `Expediente.id`; el retiro lógico no borra las relaciones. Las consultas operativas de documentos GRE deben filtrar activos.
- `PagoERP.voucher_documento_id` referencia `Documento.id`. El retiro lógico no rompe la FK ni elimina pagos, pero puede dejar un comprobante de pago retirado vinculado a pago contabilizado. **Hace falta política explícita y prueba de negocio antes de permitir eliminación definitiva.**
- `Alerta.expediente_id` y `AlertaManual.expediente_id` mantienen relaciones al retirar el expediente; la lógica de alertas se recalcula para expedientes activos, no para expedientes retirados.

## Riesgos y decisiones pendientes antes de implementar POST /expedientes/{id}/restaurar

1. Restauración de expediente completo vs. selección de sus evidencias. Debe diferenciar documentos que se retiraron por cascada de los retirados **antes** de eliminar el expediente, para no reactivar documentos previamente descartados. El evento `DOCUMENTO_ELIMINADO_CON_EXPEDIENTE` puede servir de evidencia, pero debe verificarse su conservación y trazabilidad.
2. Verificar original y SHA-256 de **cada documento candidato** antes de cambiar cualquier estado; si alguno falta, definir si se bloquea todo o se ofrece recuperación parcial supervisada.
3. Mantener límites tenant/rol/ámbito coherentes con `_visible_para_auth`, `_validar_ambito_documento` y permisos efectivos. SUPERADMIN queda fuera de las API operativas.
4. Evitar colisiones por identidad de factura/expediente, SHA y huella comercial antes de reactivar, usando transacción única y recuperación controlada de `IntegrityError`.
5. Recalcular estado, documentos faltantes, alertas y totales en la misma transacción. Verificar GRE no resueltas, vouchers vinculados y pagos ERP; no modificar pagos por restaurar un documento.
6. Añadir tests multi-tenant, cinco roles, expedientes con evidencia retirada previamente, archivos faltantes, colisiones, importes, vínculos GRE/pagos y alertas.
7. No mezclar esta función con borrado físico ni mantenimiento crítico; mantener la restauración reversible.

## Entrega segura próxima

Implementar primero pruebas de cobertura de ámbitos y relaciones con datos sintéticos. Después, diseño de restauración integral con confirmación explícita; no exponer botón hasta superar CI y pruebas en staging.
