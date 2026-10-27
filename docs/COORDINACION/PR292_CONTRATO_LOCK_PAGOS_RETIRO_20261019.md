# Contrato de concurrencia — PR #292 MISD ↔ Liquidaciones ERP

**Estado:** propuesta de interfaz para coordinación intermodular; no afirmar resuelto hasta integrar **ambos lados** y pasar pruebas PostgreSQL reales. No modifica producción.

## Evidencia sobre código de esta rama

- `POST /api/v1/responsable/.../pagos/programar` en `backend/app/api/routes/responsable.py` calcula producción y luego inserta `PagoERP`. Las consultas existentes de saldo/adelantos usan `FOR UPDATE`, **pero no protegen conjuntamente** el período de producción frente a la retirada del expediente.
- `POST /api/v1/misd/solicitudes/{id}/ejecutar` bloquea solicitud, expediente y documentos, verifica `motivo_bloqueo_liquidacion` y marca retirada. `DELETE /api/v1/expedientes/{id}` consulta liquidaciones sin utilizar el mismo lock.
- `motivo_bloqueo_liquidacion` comprueba pagos por tenant, período/fecha, moneda y el ámbito `usuario_id`, `gestor_id` y `responsable_id`. El vínculo del responsable exige resolución jerárquica actual.
- En `main...feat/document-retention-role-actions-20261018` hay divergencia: **152 commits adelante y 3 atrás**, observada al preparar este contrato. Reconfrontar inmediatamente antes de integrar.

## Contrato propuesto: recurso de exclusión mutua por tenant

Adoptar una **fila de Tenant existente** como mutex SQL transaccional conservador durante la operación crítica, usando en *todos* los escritores participantes:

```python
session.execute(
    select(Tenant.id)
    .where(Tenant.id == tenant_id)
    .with_for_update()
).first()
```

Es una solución deliberadamente gruesa, sin hash de advisory locks y sin migración; **reduce concurrencia por empresa**, por lo que se requiere medición de carga y acuerdo con propietarios de operaciones antes de habilitarla. Para transacciones multi-tenant, adquirir locks en orden ascendente de UUID. La adquisición debe ser **primera** antes de cualquier lock de expediente/documento/adelanto, para evitar deadlocks por orden inverso.

Una vez adquirido el mutex, todavía dentro de la misma transacción:

1. **Liquidaciones:** recalcular producción desde expedientes activos, verificar período, moneda y ámbito; comprobar vigencia de documentos y solicitudes incompatibles; insertar `PagoERP` y confirmar antes de liberar el lock.
2. **Retiradas:** adquirir mutex, volver a leer expediente/documentos y pagos **después** de adquirirlo, rechazar si existe liquidación o voucher vinculado y marcar `deleted_at` con auditoría. Para solicitud MISD, validar aprobación, solicitante y jerarquía vigente también después de adquirir lock.
3. **Cancelaciones/correcciones:** seguir el mismo orden y no cambiar importes ni estado de pago sin flujo autorizado.
4. **No mantener un lock abierto al hacer solicitudes HTTP, trabajo de almacenamiento, llamadas a terceros ni fuera de transacción SQL.**
5. PostgreSQL `READ COMMITTED` permite observar datos confirmados por la transacción anterior cuando las consultas se ejecutan tras adquirir el mutex. Debe verificarse que la sesión/ORM no utilice datos previamente cargados sin refresco.

## Matriz mínima de pruebas obligatorias (PostgreSQL, dos sesiones separadas)

| Carrera | Resultado exigido |
|---|---|
| Pago adquiere mutex primero | Retirada espera y retorna 409 al ver pago confirmado; pago solo incluye producción activa |
| Retirada adquiere mutex primero | Pago espera y recalcula producción activa; no liquida expediente retirado |
| Dos pagos del mismo período | Solo uno puede confirmar, segundo 409 por solapamiento |
| Dos retiradas del mismo expediente | Una marca retiro y la otra devuelve 404/409 según ruta, sin duplicar efectos |
| Error de `commit` después de modificar datos | Rollback de estado y auditoría; mutex se libera |
| Empresas diferentes | Sin contaminación entre tenants; mutex independiente |
| GRE/voucher/pago existente | No se elimina ni altera relación contable o comprobante |

## Condiciones para desbloquear PR #292

- Propietario del **módulo Rol Responsable / liquidaciones**, del módulo de **gestores** y de **MISD** acuerdan la interfaz y el orden; no sobrescribir ramas paralelas.
- Implementar la adquisición antes de **todas** las rutas que producen pagos (`PagoERP`, `PagoGestor`, `PagoResponsableERP`) y rutas de retiro MISD, incluidas directas.
- Agregar pruebas PostgreSQL con barreras, conexiones separadas y confirmación de comportamiento para ambos órdenes; revisar tiempos muertos y reintentos.
- Ejecutar CI, confrontar contra `main`, revisar Alembic, staging aislado y el procedimiento de backup/restore.
- Hasta entonces: **bloqueante de seguridad abierto; no fusionar ni desplegar.**
