# Contrato de bloqueo compartido — MISD, Rol Responsable y Gestores

Fecha: 19/10/2026. Estado: **propuesta técnica para revisión de responsables**, no implementación en rutas de pagos.

## Problema verificado

En `solicitudes_retiro_misd.ejecutar`, MISD toma `FOR UPDATE` del expediente y revisa pagos. En `responsable.programar_pago_usuario`, el cálculo de producción y la creación de `PagoERP` no toman el mismo bloqueo del expediente. El sistema puede retirar una producción mientras otra transacción computa o liquida esa producción. `motivo_bloqueo_liquidacion` consulta tres tipos de pago, pero una consulta sola no serializa inserciones concurrentes.

## Protocolo propuesto

**Clave:** tenant UUID. **Lock transaccional PostgreSQL:** tomar primero el mismo bloqueo de fila de `Tenant` mediante `SELECT id FROM tenants WHERE id=:tenant_id FOR UPDATE` en todos los caminos que cambien producción elegible, liquiden producción o retiren expedientes. No bloquear con clave de expediente únicamente, porque la liquidación calcula agregados por usuario, gestor, responsable, período y moneda. El bloqueo tenant-wide simplifica el orden y prioriza seguridad sobre concurrencia.

**Orden obligatorio:** (1) validar contexto tenant y autorización inicial; (2) adquirir fila `Tenant` una sola vez, antes de cualquier lectura de elegibilidad; (3) volver a leer expedientes/documentos/pagos activos, validar límites y referencias; (4) adquirir otros locks por ID ascendente si son necesarios; (5) calcular/actualizar/registrar auditoría; (6) confirmar o revertir la misma transacción. Nunca liberar lock antes del `commit`.

**Consumidores obligatorios:**
- MISD: `DELETE /expedientes/{id}`, `DELETE /documentos/{id}`, `POST /documentos/retirar-lote` y `POST /misd/solicitudes/{id}/ejecutar`.
- Liquidaciones: `responsable.programar_pago_usuario`, rutas que creen `PagoResponsableERP`, `PagoGestor` y recálculos/liquidaciones que dependan de documentos activos.
- Documentar las rutas de ajustes posteriores que alteren producción o pagos.

**No basta usar** `FOR UPDATE` en `PagoERP` inexistente, `Expediente` local o la mera lectura de `motivo_bloqueo_liquidacion`. El lock debe ser compartido y previo a las consultas.

## Plan de pruebas para aceptación conjunta

1. PostgreSQL real con dos conexiones: A inicia retiro y retiene lock; B intenta programar liquidación, espera; tras commit A, B lee solo producción activa y nunca paga producción retirada.
2. Invertir el orden: B bloquea/crea `PagoERP` y confirma; A reevalúa bajo el lock y rechaza retiro con HTTP 409 sin cambiar los originales.
3. Repetir para `PagoGestor` y `PagoResponsableERP`, varios períodos, monedas, tenants y vouchers vinculados.
4. Validar rollback, timeout de lock, orden uniforme de bloqueos y evitar deadlocks; comprobar todas las entradas directas, por lote y con autorización MISD.
5. Probar `backend` y `roles-real-integration` en GitHub Actions, además de regresión de migraciones. Ninguna operación sobre VPS.

## Coordinación requerida

Los responsables de **Rol Responsable**, **Gestores** y **MISD** deben acordar el contrato antes de editar sus rutas compartidas. La rama del PR #292 no debe sobrescribir implementaciones paralelas. Mantener DRAFT y NO integrar ni desplegar mientras el contrato no se adopte en todos los consumidores y se verifique con PostgreSQL.
