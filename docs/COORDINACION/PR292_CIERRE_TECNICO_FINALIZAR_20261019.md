# Cierre técnico FINALIZAR — PR #292 (19/10/2026)

## Alcance y evidencia verificada

- Rama: `feat/document-retention-role-actions-20261018`; último commit con CI validado: `87c8651ada2c6c686e234784b2194b6b79715186`.
- GitHub Actions en ese SHA: **7/7 completados con éxito** (`backend`, `frontend`, `roles-real-integration`, `roles-browser-isolated`, `recepcion-documental-ci`, `items-migration-ci`, `coordination-guardrails`).
- Reviews formales y review threads consultados: **ninguno**. Esto **no equivale** a aprobación de revisores.
- Comparación remota `main...feat/document-retention-role-actions-20261018`: **151 commits por delante y 3 por detrás**, estado `diverged`. Evitar integración sin recalcular SHA, revisar conflictos, alcance y cambios paralelos.
- Suite añadida en la rama: restauración integral selectiva (no reactiva documentos ya retirados), originales ausentes y hash corrupto, tenant ajeno, referencias GRE y voucher ERP, rollback `IntegrityError`, concurrencia PostgreSQL 200/409, permisos y alertas.

## Bloqueantes de integración (NO LISTO PARA MAIN / NO DESPLEGAR)

1. **ALTO — Exclusión mutua pago/retirada no demostrada.** Hallazgo específico documentado en `PR292_AUDITORIA_SEGURIDAD_PAGOS_ELIMINACION_20261019.md`: la emisión de `PagoERP` puede ocurrir concurrentemente con una retirada MISD si las rutas del módulo de pagos no comparten bloqueo transaccional. La prueba de dos restauraciones no demuestra seguridad pago/retirada. Requiere acuerdo con responsable de pagos y tests bidireccionales en PostgreSQL sin invadir código de otro chat.
2. **ALTO — Divergencia y dependencia de `main`.** Verificar rama base y migración Alembic `0042` (depende de `0041`), conflictos de rutas, esquema y políticas antes de integración. No hacer rebase/merge silencioso, ni forzar `main`.
3. **ALTO — Efecto de despliegue automático.** `.github/workflows/deploy-staging.yml` escucha `push` a `main`; el job `deploy` usa VPS autorizada y actualiza servicios tras pasos de preflight. **Fusionar a main podría desplegar automáticamente**. Es imprescindible aprobación *específica y separada* de este efecto y verificación de backup/restore en un entorno aislado; si no existe, no integrar.
4. **ALTO — Conservación fiscal y política de borrado definitivo.** No habilitar supresión física mientras falten aprobación, matriz legal, relación entre expedientes, pagos, guías, documentos referenciados y recuperación demostrada.
5. **MEDIO — Política jerárquica y contrato compartido.** Hay lógica nueva de revalidación en `solicitudes_retiro_misd.py` y reglas de SECRETARIA: revisar consistencia efectiva con `docs/COORDINACION/PR292_CONTRATO_MISD_OCR_PDF_PENDIENTES.md` antes de declarar terminado el contrato. Validar roles con casos HTTP y tenants activos.
6. **MEDIO — Validación de recuperación.** Probar backup real con restore aislado y rollback de migración `0042`; el CI de ramas no verifica el estado actual de la VPS.

## Preparación de integración (no ejecutada)

1. Coordinar lock común con módulo de liquidaciones/pagos y crear regresión de carrera pago/retirada.
2. Revalidar permisos y contrato MISD con dueños de roles/OCR; mantener el PR en `draft` si quedan riesgos.
3. Actualizar comparación contra `main`, conflictos, dependencias, reviewers, checks y SHA inmediatamente antes de integrar.
4. Comprobar entorno staging **realmente aislado de la VPS productiva**, backup, restauración y recuperación.
5. Solicitar una autorización **para integrar** y, separadamente, autorización explícita **para el despliegue automático potencial**. Sin esas autorizaciones: detener.

## Decisión

**Cierre técnico documentado con bloqueantes abiertos; PR #292 permanece DRAFT y NO APTO PARA INTEGRACIÓN/DESPLIEGUE.** No se tocó `main`, VPS, producción ni OCR/NEXUS en este cierre.
