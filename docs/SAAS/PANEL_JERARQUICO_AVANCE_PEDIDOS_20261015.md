# FACT CENTRAL — Panel jerárquico de pedidos (especificación de implementación)

## Decisiones funcionales confirmadas (2026-10-15)

1. **Solo un miembro con rol RESPONSABLE puede recibir pedidos de Gerencia**. GERENTE emite; USUARIO/GESTOR/proveedor nunca son destinatarios de pedidos gerenciales.
2. Pedido **GLOBAL**: presupuesto total destinado a Responsable; este crea asignaciones por receptoras, luego por sus Usuarios y Gestores/proveedores. Mientras no se distribuya no atribuir presupuesto ficticio a una receptora.
3. Pedido **ESPECIFICO**: Gerencia fija importes por receptora para un Responsable. Responsable distribuye entre proveedores mediante Usuarios/Gestores sin cambiar techo autorizado salvo permiso explícito.
4. USUARIO **solo consulta** en este flujo: barra general propia, tarjetas de **sus Gestores seleccionables**, y debajo receptoras de Gestor seleccionado. No ingresa facturas ni crea pedidos. Aplicar esta norma también en rutas/API y no solo ocultar botones.
5. GESTOR carga y valida documentos conforme a las capacidades efectivas del rol; ve barra agregada + barras por receptora de su cartera.
6. RESPONSABLE ve barra global, Usuarios seleccionables y receptoras de cada Usuario. GERENTE ve barra global, Responsables seleccionables y receptoras de cada Responsable.
7. Con pedido de S/ 10,000: verde < 10,000; naranja 10,000 a 12,000 inclusive; rojo > 12,000, si tolerancia=20%. La tolerancia es configurable entre 0 y 20%, predeterminado 20%. Permitir registrar facturas reales sobre el máximo, generar alerta y advertir de detener futuras compras.
8. Una misma factura válida se suma una vez, según relación expediente/operación, importe original y moneda; tratar anulaciones, cambios, duplicados, multicurrency y permisos de manera consistente.
9. El indicador **global** es suma ejecutada / suma autorizada, no promedio de porcentajes. Barra visual se satura al máximo del carril; mostrar porcentaje real incluso >120%.
10. Mantener intacto el dashboard existente debajo del panel. Actualización por consulta periódica y/o eventos de invalidación; el backend aplica restricciones por tenant + jerarquía.

## Restricciones de compatibilidad

- Estado actual main: PedidoGerencia tiene unicidad (tenant_id,gerente_id,cliente_id,periodo_mes,moneda), responsable_id opcional. Por eso PR #211 **no** soporta de forma correcta un pedido global a Responsable sin receptoras y hay que rediseñar cuidadosamente antes de integrarlo.
- Separar entidad cabecera `pedido_responsable` (solicitud y período) de presupuestos por receptora, asignaciones a Usuario/Gestor/proveedor y facturas imputadas; estudiar migración de pedidos existentes sin pérdida de historiales ni pagos.
- No exponer nombres/importes de otros equipos: para GERENTE cartera y Responsables vinculados, RESPONSABLE Usuarios vinculados, USUARIO solo Gestores propios, GESTOR solo sus asignaciones.
- Refrescar datos solo desde endpoints autorizados, nunca confiar en ID de integrante recibido desde interfaz.
- Sin registros de compras ficticios, ni división artificial de comprobantes. Documentación real verificable.

## Secuencia y criterios de aceptación

1. Inventario de modelos, endpoints y roles; esquema y migración reversible; pruebas de datos existentes.
2. API de pedido global a Responsable y pedido específico por receptoras; presupuestos no podrán exceder cabecera sin autorización explícita; transacción atómica + auditoría.
3. API de asignaciones y ejecución documental, montos por receptor/usuario/gestor y moneda.
4. Endpoint jerárquico de lectura con totales, miembros seleccionables, receptoras y estado de semáforo. Pruebas de aislamiento intertenant e inter-rol.
5. Componente de tablero con barra global, tarjetas seleccionables de subordinados, barras de receptoras, recuentos de expedientes, filtros de mes y moneda, estados carga/error y refresco.
6. Pruebas de límites exactos 99.99%,100%,120%,120.01%, cancelaciones, dobles ingresos, tolerancia y permisos; CI backend/frontend/integración.
7. Revisión, respaldo restaurable y despliegue **solo VPS antigua app.nexomarnegocioseirl.online**. No tocar Oracle nueva.

## Avance en esta rama

El Dashboard de USUARIO tiene selección contextual de Gestores y el desglose actual de empresas receptoras. **Todavía no hay cálculo ni barras de avance de presupuestos**: dependen de los puntos 1-4. No simularlos con sumas de expedientes.
