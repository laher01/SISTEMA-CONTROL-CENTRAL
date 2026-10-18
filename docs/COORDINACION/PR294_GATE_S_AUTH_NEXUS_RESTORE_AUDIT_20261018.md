# Gate S — cierre técnico en rama de pruebas (18/10/2026)

**Estado: S OPEN. No merge, VPS ni despliegue.**

## Trabajo comprobado y en curso
- PR #293 commit probado `5b6633e13dc31fe69f2c3d679b97cf7209b89c49`: workflows backend `39111038202`, recepción `39111038107`, roles `39111038136` y coordinación `39111038198` en SUCCESS; la documentación posterior no sustituye un nuevo CI por SHA.
- PR #294 DRAFT, commit `98f9ed6a4cdfd1f11e65d7101ab191615ea492fb`: test de dos inicios de sesión reales vía `/api/v1/auth/login` y cookies firmadas por sesión de base de datos, con denegación API cruzada y datos sintéticos. Su CI se inició: `39140559306` recepción, `39140559348` backend y `39140559358` roles; resultados aún pendientes al elaborar registro.

## Auditoría de flujo de código (no confundir con evidencia E2E)
- `backend/app/api/routes/auth.py`: login filtra cuentas por tenant/código o nombre, verifica hash de clave, genera sesión y cookie segura.
- `backend/app/api/deps.py`: `get_contexto_actual` lee la cookie, resuelve token y valida tenant del host; `get_contexto_operativo` restringe roles.
- `backend/app/services/ingesta.py`: filtros por tenant, unicidad de factura por expediente, bloqueo en `Expediente` y procesamiento de ítems UBL; `ReferenciaGRE` puede registrar relación provisional sin inventar factura.
- `backend/app/services/referencias_gre.py`: extrae referencias fiscales explícitas GRE y rechaza contradicciones de RUC para la misma factura.

## Bloqueos concretos para Gate S
1. Validar CI de PR #294 y corregir exclusivamente pruebas sintéticas si fallan.
2. Ejecutar pruebas de extremo a extremo de GRE-voucher-FACT-items en el mismo tenant y de rechazo de un vínculo entre tenants con efectos económicos nulos; registrar IDs y sumatorias esperadas.
3. Identificar eventos reales NEXUS en código (productor, consumidor, persistencia, control de duplicados), sin inventar un bus. Si no existen, declarar función excluida de staging.
4. Entorno de staging autorizado y completamente separado de producción: variables, DNS, credenciales, red, DB, archivos, backups y HTTPS.
5. Respaldo pareado real/autorizado de PostgreSQL+almacenamiento, manifest SHA256, restauración aislada y reconciliación de expedientes (FACT/GRE/voucher/ítems).
6. Prueba de Alembic y rollback sobre respaldo restaurado; comprobar RBAC y eliminación segura de datos de prueba posteriores al ensayo.
7. Healthchecks, observabilidad, pruebas de contingencia, revisión independiente de código y aprobación explícita del responsable.

## Límites
No se accedió al servidor ni a secretos ni a datos reales. Las pruebas usan cuentas/documentos sintéticos. No modificar `main` ni PR #264, #290 o #293; todos DRAFT. El PR #294 también DRAFT.
