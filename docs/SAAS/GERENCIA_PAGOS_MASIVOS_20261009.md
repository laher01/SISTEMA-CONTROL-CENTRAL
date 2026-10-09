# Ajustes del panel Gerente — Pagos ERP (09-10-2026)

## Cambios de interfaz entregados en esta rama
- **Pago a Responsables:** selector de Responsable antes de ver detalles; opciones cargadas del endpoint autorizado `/api/v1/pagos/responsables`. Se muestran solo las empresas, totales y liquidaciones del Responsable seleccionado. Filtro por **mes** sincronizado con **desde / hasta** editables, manteniendo moneda.
- **Consolidado:** las tarjetas se ajustan al ancho real del importe, con texto que se puede dividir y diseño flexible. Evitar el desborde incluso con cifras altas.

## Requerimiento pendiente: presupuestos masivos
Conservar la creación de pedido individual y agregar un modo **Presupuesto masivo**:

1. Seleccionar mes y moneda; cargar exclusivamente clientes de la cartera autorizada al Gerente.
2. Mostrar filas con selección por Cliente/Receptor y RUC, campo de importe individual, más botón «Aplicar monto a seleccionados».
3. Después de aplicar importe general, permitir editar importes individuales sin perder selecciones.
4. Elegir uno o más Responsables de la cartera autorizada. Aclarar en vista previa que **el importe de cada receptor se asigna a cada Responsable seleccionado** (si hay tres responsables seleccionados, el pedido se repite para cada uno). Total = suma de importes por receptor * número de responsables.
5. Antes de crear: vista previa del número de órdenes, subtotal, total y advertencias de duplicidad; confirmación explícita.
6. Un único endpoint **transaccional, idempotente y auditable** crea el lote completo: validar tenant, Gerente, cartera de receptores, vínculos gerente/responsables, mes, moneda, importes positivos, y conflictos preexistentes; fallar sin grabaciones parciales si una combinación es inválida.
7. Guardar identificador de lote, relaciones pedido→responsable, usuario que creó, instante, importe solicitado; mostrar historial y permitir reversión solo para elementos sin ejecución ni asignaciones, bajo reglas existentes.
8. La producción efectiva se obtiene de Expedientes procesados, no del importe presupuestado. No confundir presupuesto con cobro o comisión.

### Obstáculo real detectado en el esquema actual
La tabla `pedidos_gerencia` usa la restricción única
`(tenant_id, gerente_id, cliente_id, periodo_mes, moneda)`.
Así, un Gerente **no puede** crear dos pedidos para un mismo Cliente, mes y moneda destinados a Responsables distintos.

Antes de activar el modo masivo para varios Responsables, decidir una migración con integridad: introducir entidad principal de presupuesto por gerente/cliente/mes/moneda y sus asignaciones por responsable, o modificar con cuidado la unicidad y las consultas vinculadas por `pedido_gerencia_id`. Debe mantenerse compatibilidad con históricos y no duplicar producción. **No liberar** una implementación que haga N peticiones independientes y deje pedidos a medias si una falla.

## Pruebas obligatorias antes del despliegue
- Responsable sin producción visible en selector, con tabla vacía y ninguna filtración de otras empresas.
- Filtros mes completo y rango arbitrario; cambio de moneda; liquidaciones pagadas, adelantadas y reprogramadas.
- Consolidado desde S/ 0 hasta cifras de ocho o más dígitos en escritorio y móvil.
- Bulk: uno y varios Responsables; variación individual de importes; receptor desmarcado; duplicados; tenant equivocado; vínculo no autorizado; rollback atómico; reintento seguro sin pedidos duplicados; cálculo del total.
- API tests, typecheck/build frontend, migraciones y autorización antes de publicar a VPS.

## Despliegue
Rama de revisión únicamente; no implica cambios en el VPS hasta que estén completas las pruebas y la funcionalidad masiva.
