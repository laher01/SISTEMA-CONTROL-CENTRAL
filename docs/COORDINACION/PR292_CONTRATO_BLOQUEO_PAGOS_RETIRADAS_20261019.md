# Contrato de bloqueo compartido — MISD, Rol Responsable y Gestores

Fecha inicial: 19/10/2026. Revisión de correspondencia código/documento: 19/10/2026.

## Historial y alcance

La propuesta inicial de este documento planteaba `SELECT ... FOR UPDATE` sobre la fila `Tenant` en todos los consumidores. **Esa propuesta no describe el mecanismo implementado en el HEAD del PR #292**. Se conserva aquí como antecedente, no como instrucción vigente. El PR #336 (aún no integrado) modifica `bloqueo_produccion.py` para delegar en el bloqueo financiero común; no se debe describir como integrado antes de su fusión y comprobación.

## Contrato implementado actualmente en PR #292

- Identificador de aislamiento: UUID de tenant, derivado de la sesión y el contexto autorizado.
- Primitiva PostgreSQL: `pg_advisory_xact_lock(hashtextextended(:clave, 0))`, con `clave = "fact-central:misd-liquidacion:" + tenant_id`. Está definida en `backend/app/services/bloqueo_financiero_misd.py`.
- Propiedad: **transaccional**, retenida hasta COMMIT o ROLLBACK; todas las rutas incompatibles deben usar la misma clave dentro de la misma transacción.
- En SQLite la función no adquiere un advisory lock PostgreSQL: las pruebas de exclusión mutua reales exigen PostgreSQL y dos conexiones.
- Consultar liquidaciones con `motivo_bloqueo_liquidacion` no sustituye la serialización; tampoco basta `FOR UPDATE` de una fila de expediente o pago distinto.

### Orden requerido para cada ruta de mutación

1. Validar contexto de tenant y autorización inicial.
2. Adquirir `bloquear_tenant_financiero(session, tenant_id)` **antes** de consultar producción elegible, pagos, documentos activos o referencias cuya validez dependa de la concurrencia.
3. Reconsultar los datos de elegibilidad ya bajo el bloqueo y adquirir bloqueos específicos en orden estable cuando corresponda.
4. Validar permisos y relaciones vigentes; registrar retiro, liquidación y auditoría.
5. Realizar COMMIT o ROLLBACK de la **misma transacción**.

### Evidencia inspeccionada, no cobertura certificada

En el HEAD `c2c686011e44831bb6487263c3e723e9e171097d` de PR #292 se encontró uso de `bloquear_tenant_financiero` en:

- `backend/app/api/routes/responsable.py` (programación de pagos de usuario);
- `backend/app/api/routes/pagos_responsables.py` (pagos a responsables);
- `backend/app/api/routes/pagos_gestores.py` (pagos a gestores);
- `backend/app/api/routes/expedientes.py` (retirada de expedientes);
- `backend/app/api/routes/documentos.py` (retirada documental).

El flujo `backend/app/api/routes/solicitudes_retiro_misd.py` también importa y utiliza el mismo bloqueo. **Presencia del llamado no certifica** que todos los caminos de lote/retirada directa/pagos lo obtengan antes de leer elegibilidad; requiere revisión y pruebas de carreras completas. La migración financiera y los controles fiscales no pueden declararse seguros solo por resultados unitarios.

## Corrección aislada del PR #336, todavía pendiente

El PR #336, HEAD `9672152de10415c23e5eac053fb7445fe8271ecc`, propone que `bloquear_tenant_para_produccion` sea alias de `bloquear_tenant_financiero` y añade prueba PostgreSQL de exclusión bidireccional para ambos nombres; su CI previo es 4/4 exitoso. La rama base #292 contiene la versión anterior. **No asumir convergencia completa de consumidores hasta integrar #336, volver a ejecutar CI y revisar rutas HTTP reales.**

## Pruebas necesarias antes de integración a main

1. Dos sesiones PostgreSQL: retirada retiene lock; pago espera y reevalúa para no liquidar producción ya retirada.
2. Orden inverso: pago confirma primero; retirada bajo lock reevalúa y rechaza con HTTP 409 cuando corresponda.
3. Repetir para `PagoERP`, `PagoGestor`, `PagoResponsableERP`, retiro individual/por lote y ejecución autorizada de solicitud MISD.
4. Aislamiento entre tenants, rollback, errores de integridad, cambios de período/moneda y tiempo de espera/deadlock.
5. Verificar en pruebas de API que el lock precede a lecturas de elegibilidad y se conserva en transacción hasta el commit.
6. Ejecutar CI sobre SHA resultante de cualquier integración; respaldos/restauración VPS pertenecen al módulo especializado.

## Límites de responsabilidad y trazabilidad

Esta corrección **solo actualiza documentación de MISD**; no cambia contratos de pagos compartidos ni código ajeno, ni altera política fiscal de conservación. La eliminación física sigue deshabilitada mientras no existan autorizaciones y recuperación acreditada.

Referencias: PR #292, PR #336, issue #340 (dependencia Etapa 7), documento histórico `PR292_CIERRE_TECNICO_FINALIZAR_20261019.md`. No fusionar a `main` ni desplegar con base en esta documentación.
