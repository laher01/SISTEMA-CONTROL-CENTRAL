# Issue #242 — Contrato funcional: pedido original y asignaciones

Estado: especificación de implementación; **NO implementado** ni apto para despliegue.

## Alcance y compatibilidad

FACT CENTRAL es SaaS multi-tenant. El pedido de Gerencia se emite exclusivamente a un Responsable. Cada operación real puede asociarse a su pedido y a sus asignaciones sin fabricar comprobantes ni distribuir automáticamente facturas entre empresas.

- `GLOBAL`: un pedido por monto total, con receptoras distribuidas posteriormente por el Responsable.
- `ESPECIFICO`: un pedido original con detalles de montos por receptora y un único Responsable destinatario.
- Responsable asigna a Usuarios; Usuario asigna a sus propios Gestores. Gestor registra operaciones y documentos reales. Usuario supervisa y no emite comprobantes.
- Avance = monto documentado válido y no duplicado / presupuesto válido; consolidar mediante suma de importes, nunca promediar porcentajes.
- Semáforo: menor de 100 % verde; 100 % a 120 % inclusive naranja; más de 120 % rojo. Los excesos no bloquean registrar compras reales: generan avisos.
- Pago: Gerente → Responsable y Responsable → Usuario. Cobro inverso. Pago Usuario → Gestor queda fuera del alcance. Reutilizar políticas existentes de comisiones y liquidaciones.

## Restricciones comprobadas en main

En el esquema actual `PedidoGerencia.cliente_id` es obligatorio, y existe unicidad por `(tenant_id, gerente_id, cliente_id, periodo_mes, moneda)`. `AsignacionPedidoGerencia` asocia `pedido_id`, `usuario_id` y opcionalmente `gestor_id`, `proveedor_id`. Por ello **el PR #211 no debe integrarse tal como está**: el endpoint masivo genera varios pedidos originales para un único encargo.

## Pasos de implementación antes de declarar apto

1. Diseñar y probar una migración compatible con todos los pedidos históricos; decidir mediante revisión del esquema si corresponde una entidad principal o evolución del modelo, sin romper relaciones `Expediente.pedido_gerencia_id` ni pagos existentes.
2. Persistir una clave inequívoca de pedido original por Tenant y la modalidad; registrar detalles por receptora y asignaciones jerárquicas con permisos de servidor.
3. Garantizar idempotencia ante envío repetido, transacciones atómicas, trazabilidad de auditoría e independencia entre Tenants incluso cuando se conozcan UUID ajenos.
4. Probar el reparto sin sobreasignaciones inadvertidas, cumplimiento de cartera y vínculo de roles, protección frente a doble conteo y documentos anulados.
5. Reutilizar PR #210, #212, #200 y #102 tras reconciliar con main, evitando duplicar pantallas de pagos/cobros.
6. Probar migración sobre una copia restaurada, flujo completo de roles, políticas de comisiones, pruebas backend/frontend y recuperación; solo después considerar fusionar y desplegar a VPS antigua.

## Criterios de aceptación mínimos

- Un encargo de Gerencia produce exactamente un identificador de pedido principal y N asignaciones, no N pedidos independientes.
- Las receptoras y los importes específicos conservan su detalle y suma, sin perder la identidad del destinatario Responsable.
- Roles no vinculados y otros Tenants reciben denegación sin revelar datos.
- El historial previo permanece accesible y no altera importes pagados.
- Cualquier fallo en las pruebas impide integración y despliegue.

**Coordinación:** este documento desarrolla el Issue #242; los cambios en modelos, migraciones, autenticación y workflows compartidos requieren comunicación previa con sus responsables.
