# Contabilidad de Ítems — contrato de integración (borrador técnico)

> Estado: diseño en rama aislada; no habilitado para producción.
> Mantener intactas las reglas de expedientes, OCR y eliminación desarrolladas en paralelo.

## Objetivo
Procesar líneas de factura y conservar **cantidad, unidad, descripción original, producto canónico y referencia al comprobante**. Mostrar acumulados por categoría / producto / unidad y acceso al desglose por emisor, receptor, fecha y jerarquía operativa.

## Entidades propuestas
- `categorias_items`: tenant_id, id, padre_id, nombre, activo.
- `productos_items`: tenant_id, id, categoria_id opcional, denominacion_canonica, marca, presentacion, variante, unidad_base, estado_clasificacion (CONFIRMADO / POR_CATEGORIZAR), confianza, activo.
- `alias_productos_items`: tenant_id, producto_id, texto_normalizado, descripcion_original, fuente, confirmado_por; no unir variantes si falta información.
- `lineas_comprobantes`: tenant_id, expediente_id, documento_origen_id, numero_linea, producto_id opcional, descripcion_original, cantidad Decimal, unidad, precio_unitario, importe_linea, estado_extraccion, huella_linea. Una línea única por origen documental, número de línea y versión confirmada; el reprocesamiento debe ser idempotente.
- `reglas_items_empresa`: tenant_id, empresa_id, producto_id/categoria_id, decision (PERMITIDO/OBSERVAR/RESTRINGIDO), motivo, vigencia y actor. No activar restricciones en otras empresas.
- `auditorias_items`: tenant_id, expediente_id, producto_id, acción, estado, motivo, solicitante, aprobador, fechas y eventos inmutables.
- `alertas_items`: tenant_id, expediente_id, destinatario, motivo, estado, fecha, deduplicación.

## Estados y decisiones
- NEXUS solo **sugiere** categorizaciones y genera observaciones; no invalida automáticamente.
- Secretaría propone desactivación/reactivación y queda **pendiente de aprobación**.
- Administración o gerencia pueden confirmar o revertir propuestas; registrar actor y evitar autoaprobación.
- Todos los ítems de un comprobante con invalidación **confirmada** quedan fuera del acumulado operativo. Una invalidación pendiente se muestra por separado y no debe borrarse ni presentarse como invalidez tributaria.
- Los estados operativos no alteran la factura fuente, ni sustituyen validación SUNAT. Un producto ajeno al giro es alerta, no causal automática de invalidez fiscal.
- La acción sobre productos compartidos necesita alcance explícito (empresa/tenant): ninguna regla global accidental.

## Consultas propuestas
- Listado: categoría, producto, descripción, unidad, cantidad acumulada, estado, Consultar.
- Filtros: fecha desde/hasta, día, mes, emisor, receptor, gerente, responsable, usuario, gestor, estado.
- Detalle: pestañas General, Proveedores y Clientes; fecha, RUC y razón social de ambas empresas, importe por línea y cantidad con unidad, responsable/usuario/gestor autorizados.
- Seguridad: filtrar siempre tenant y alcance de cartera en el backend, **no solo en el frontend**.
- No sumar CAJA y PAQUETE automáticamente ni convertir a unidades sin equivalencia registrada.
- Las notas de crédito deben revertir cantidades mediante vínculo explícito, no valores negativos arbitrarios.

## Exportación e impresión común
Casillas y selección múltiple en Documentos, Registros, Expedientes y Contabilidad de Ítems. Operaciones autorizadas: PDF individual, PDF consolidado, ZIP de originales, Excel, imprimir vista y eliminación lógica (según rol). Una sola descarga directa sin pantalla intermedia. No generar ni distribuir RAR sin soporte confirmado. Debe existir un componente de selección común y endpoints autenticados con validación de alcance, tamaño máximo y auditoría.

## Plan de pruebas y despliegue
1. Revisar CI existente de la rama y resolver fallos.
2. Contrastar migración Alembic con **head efectivo** de main antes de asignar revisión. No crear una nueva rama de migración sobre heads duplicados.
3. Validar PostgreSQL real: índices únicos e idempotencia; tenant; visibilidad por rol; sumas; aprobación y reversión; alertas; exportaciones; notas de crédito.
4. Probar frontend y regresiones de OCR/documentos/expedientes; comprobar las PR en curso antes del merge.
5. Requerir CI verde, backup y restauración aislada validada, y despliegue manual protegido únicamente a la VPS antigua autorizada. No tocar Oracle.
