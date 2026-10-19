# CIERRE TÉCNICO — Contabilidad de Ítems y 000 VPS (19-10-2026)

**Estado:** desarrollo candidato validado, NO integrado ni desplegado. Cierre técnico de revisión, no aceptación de producción.

## Evidencia por SHA
- main observado: `e24599110f95b2f089fffd54ae013f827d3ae7ef`.
- PR #327 DRAFT, HEAD `8dac6e39aa3f68e5452e70f23ebb6bbc89c3692b`, mergeable true y sin atraso respecto a main. 0 reviews. CI **5/5**: backend 39213552413, frontend 39213552409, roles-browser-isolated 39213552439, roles-real-integration 39213552448, recepcion-documental-ci 39213552520; todos SUCCESS.
- Backend #327, job del run 39213552413: **559 passed, 10 warnings in 126.12s**. `test_contabilidad_items_persistencia.py` 8 aprobados; `test_contabilidad_items_reescaneo.py` 15 aprobados; `test_alembic_0034_integracion.py` 1 aprobada, migración PostgreSQL efímera. También prueba HTTP de facturas/productos, roles y filtros.
- PR #330 DRAFT, HEAD `c5049451047db851e98839c2086ca1ca054e38b7`, mergeable true y 0 reviews; `preflight-safety-ci` 39217559290 SUCCESS, `deploy-staging` 39217559295 SUCCESS; `verify-backend` SUCCESS, `verify-frontend` SUCCESS, `deploy` SKIPPED por pull_request.
- PR #330 modifica solo una condición del job deploy en `.github/workflows/deploy-staging.yml` para requerir `workflow_dispatch` sobre main; preserva CI, secretos, verificación SHA, preflight, backup/restore y bootstrap.

## Bloqueantes comprobados
1. El workflow de main tiene aún `deploy.if: github.ref == 'refs/heads/main'` y `on.push.branches: [main]`: fusionar el primer gate #330 podría desencadenar despliegue automático según la definición activa/resultante y configuración. **NO realizar I hasta autorizar y acreditar transición segura.**
2. No hay reviews aprobatorias en #327/#330. No se conocen reglas de branch protection/rulesets ni la política real de Environment staging (required reviewers, bypass, restricciones); las herramientas GitHub conectadas no exponen dichos ajustes. No afirmar que existe control humano obligatorio.
3. Migración y recuperación de la **base real** no verificadas, por prohibición de acceder a VPS en esta etapa; los tests efímeros no son sustituto del respaldo/restauración de producción.

## Plan secuencial — autorizaciones separadas
**Seguridad previa:** encargado del frente 000 verifica Settings → Rules/Branches (main: reviews/status checks/bypass), Settings → Environments → staging (aprobaciones, restricciones, bypass), workflows de push main y un procedimiento controlado para primera instalación del gate sin despliegue involuntario. Prueba y registra evidencia. No desactivar CI ni mecanismos de seguridad.
**I — integrar gate #330:** solicitar aprobación expresa de la fusión **y del efecto potencial de despliegue automático** antes de tocar main. Si ese efecto no está autorizado, bloquear la fusión hasta garantizar que no ocurrirá. Verificar SHA base/head, aprobaciones, CI y no-bypass; validar en Actions que el push a main deja deploy SKIPPED.
**I — integrar Ítems #327 (etapa independiente):** solo tras comprobar que el gate está integrado y funcionando en main. Reconfrontar SHA base/head, revisión, CI, conflictos y protecciones; fusionar con autorización I específica. Verificar CI en main y que deploy es SKIPPED.
**D — desplegar VPS (autorización nueva y separada):** comprobar destino aprobado, commit de main explícito, respaldo reciente y restauración comprobada en DB aislada, esquema Alembic real y plan de vuelta atrás. Disparar manualmente workflow aprobado y cualquier aprobación de entorno; constatar containers/servicios/healthcheck, esquema y migración, trazabilidad de documentos y aislamiento tenants. Si fallan controles, abortar/recuperar según plan aprobado. No inferir resultados.
**Aceptación funcional:** iniciar sesión con roles administrador/gestor/responsable/usuario y al menos dos tenants de prueba; importar facturas XML válidas con varias líneas y unidad/moneda, validar idempotencia y concurrencia; búsquedas por descripción original y producto, categorías, rango de fechas y emisor/receptor; conciliación por moneda sin doble conteo; CSV con mismos filtros y límites; facturas vinculadas y acceso autorizado a expediente; retirar documento y constatar exclusión sin destrucción fiscal; reescaneo histórico permitido con límites/ruta/hash y control de permisos; probar ausencia de filtración entre empresas. Registrar capturas y resultados, sin datos personales expuestos.
**Cierre productivo:** ACTA de aceptación y commit desplegado, pruebas de salud y restauración, responsables, fallos, rollback y autorización final.

## Archivos/alcance
No se cambian archivos funcionales, workflow, configuración GitHub, main ni VPS por este documento. No merge, no deploy. PR #327 y #330 siguen en DRAFT. El cierre declara **READY FOR AUTHORIZATION**, no 'en producción'.
