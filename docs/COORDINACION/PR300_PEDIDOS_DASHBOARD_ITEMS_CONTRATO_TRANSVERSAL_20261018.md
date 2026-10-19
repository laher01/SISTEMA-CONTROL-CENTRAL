# Gate S — Frontera entre seguimiento de pedidos y Contabilidad de Ítems (18/10/2026)

## Verificación de fuentes
- #300 HEAD `2f2a466aec940f04476ce8087bed0aad31976c76`: Backend, Recepción Documental, Roles e Integración y Coordination Guardrails: **4/4 SUCCESS**.
- #211 `11c8c9b4669ac4878d8aecfefd542c336e9014e2`: presupuesto masivo por empresas receptoras, cambios en `backend/app/api/routes/pagos.py` y `frontend/src/paginas/Pagos.tsx`; no acredita por sí solo avance jerárquico final.
- #212 `14fb6583825c7779871291c96197d3b51da16a00`: `frontend/src/paginas/Dashboard.tsx` y `docs/SAAS/PANEL_JERARQUICO_AVANCE_PEDIDOS_20261015.md`. La documentación precisa: **no existen aún barras ni cálculo de avance de presupuestos**. Sí existe selección contextual de gestores y desglose de receptoras.
- #186 `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`: menú **Contabilidad de Ítems**; gestión de líneas, cantidad, unidad, descripción, producto y desglose proveedor/cliente por emisor/receptor. **No es el propietario del progreso presupuestal de pedidos**.

## Propiedad funcional y límites
- Gerencia y Dashboard jerárquico (#211, #212): pedidos GLOBAL/ESPECÍFICO, presupuestos, asignaciones, progreso por Responsable→Usuario→Gestor→proveedor y receptora. Solo RESPONSABLE recibe el pedido de Gerencia.
- Contabilidad de Ítems (#186, #281): extraer y preservar las líneas UBL, idempotencia por tenant/documento/línea, cantidades/unidades, catálogo y detalle por emisor/receptor. No inventar asignaciones de pedidos al contabilizar ítems.
- Gate S (#300): pruebas transversales entre pedido/factura/expediente/ítems, permisos y semáforos; sin crear un dashboard alterno.

## Contratos para aprobación por propietarios
1. Progreso bruto por pedido y moneda: `ejecutado_valido / autorizado` si autorizado > 0; mostrar ejecución real incluso superior a 100%, sin promediar porcentajes por hijo. Denominador 0/no asignado: **SIN PRESUPUESTO**, no 0%.
2. Jerarquía: GERENTE→RESPONSABLE→USUARIO→GESTOR→proveedor; receptoras por asignación efectiva. No inferir destinatario a partir de documentos no imputados.
3. Comprobante único por expediente/operación y moneda; GRE, voucher, línea OCR repetida, recibo y reprocesamiento no duplican avance. Definir correctamente notas de crédito y anulación, y excluir pendientes según política de aprobación.
4. Semáforo confirmado en documento #212: verde si ejecutado < 100%; naranja desde 100% hasta 120% inclusive; rojo >120% cuando tolerancia=20%. Tolerancia configurable 0–20%; alerta si se excede, sin falsificar operación.
5. Separar progreso de importe de facturas del volumen de ítems: un pedido en S/ no se mezcla con cantidad de pota expresada en kg o caja.
6. Backend aplica tenant/cartera/jerarquía. Usuario solo consulta, gestor registra documentos dentro del rol; no confiar en controles visuales.

## Casos transversales aún pendientes de prueba real
- Pedido específico por receptora con 2 proveedores; asignaciones explícitas; 2 facturas válidas y GRE/voucher por cada una; comprobar porcentaje por proveedor, cliente y total.
- Pedido global sin asignación a receptoras: cero atribución ficticia.
- Factura repetida, borrada o restaurada; cálculo sin doble contabilización.
- Cambio de rol o actor fuera de cartera; denegación de datos.
- Igualdad exacta de umbrales 100/120% y >120%, multicurrency y tolerancia variable.
- Validar que resumen del menú Ítems contabilice líneas originales/categorías sin atribuirse presupuesto no asignado.

## Conclusión
El indicador de avance solicitado pertenece al frente Dashboard/Pedidos (#211/#212), aún **parcial**. El menú Ítems pertenece a #186/#281. Gate S valida el vínculo; no implementa un segundo motor. Sin evidencia de integración real, no afirmar que el porcentaje está funcionando en producción. Gate S OPEN, sin merge, VPS ni despliegue.
