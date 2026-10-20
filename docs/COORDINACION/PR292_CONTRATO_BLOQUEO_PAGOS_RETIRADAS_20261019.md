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

## Evidencia adicional de regresión aislada (20/10/2026)

Las ramas **TEST ONLY** de MISD ejecutaron controles PostgreSQL sobre la combinación de la base #336 y el cambio de orden de bloqueos propuesto en #355. **Estas pruebas no integran automáticamente los PR funcionales**.

- PR #358: 595 pruebas aprobadas; independencia del bloqueo entre tenants distintos y liberación al hacer rollback.
- PR #360: 598 pruebas aprobadas; compatibilidad combinada con Alembic `0041`, orden del lock antes de acceder al estado de `solicitar`, `resolver` y `ejecutar`.
- PR #361: 600 pruebas aprobadas; dos llamadas HTTP (`solicitar` y `resolver`) esperan un advisory lock retenido por otra conexión y continúan después de liberarlo.
- PR #362: 601 pruebas aprobadas; al confirmar un `PagoERP` en una segunda transacción mientras se intenta ejecutar retirada, esta retorna HTTP 409 sin marcar el expediente como retirado ni consumir la solicitud.
- PR #364, HEAD `2e74db77b31370c8a35dd3fbf37fe31bd0653ed4`: **602 pruebas aprobadas, 10 advertencias, 3/3 CI exitosos**. Se comprueba la ruta HTTP real `/responsable/pagos/programar` bajo lock y la posterior denegación HTTP 409 de la retirada. La prueba respeta el contrato económico de dos tasas, sin admitir `porcentaje_manual` en liquidaciones nuevas.

Las cifras son **totales sucesivos de suites de pruebas**, no cantidades acumulables de casos independientes. Los PR #358, #360, #361, #362 y #364 son evidencia **TEST ONLY y no deben fusionarse**. Las regresiones pertinentes ya se copiaron al PR funcional #355, HEAD `37184714fe932958860cae20593d3dc73001e030`: sus nueve pruebas nuevas pasan en los jobs `backend` y `test`, pero cada job registra **598 aprobadas y 3 fallidas** por la misma ausencia de padre Alembic `0041` en la base #292; `integration` falla al preparar esa dependencia. No atribuir esas tres fallas a los casos de concurrencia.

**Cobertura pendiente sin afirmar:** ejecución efectivamente simultánea de **ambas rutas HTTP** de programación de pago y retirada, con intercalación y revalidación según quién consiga primero el bloqueo; escenarios análogos de `PagoGestor` y `PagoResponsableERP`, y evaluación de contención/deadlocks bajo carga. La prueba #364 serializa la programación y verifica después la retirada, no es prueba de simultaneidad completa de ambos endpoints.

**Condición de integración:** resolver formalmente P1/P2 en #336, incorporar primero #336 hacia #292 y ejecutar CI sobre el SHA resultante; continuar después con #355 y finalmente esta documentación #354. Ninguna evidencia TEST ONLY autoriza fusión con `main`, modificación de Landing/CMS ni despliegue.
