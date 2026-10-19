# Seguridad — GO/NO-GO primera integración PR #330 (19/10/2026)

Documento de revisión, **no autorización**. Basado en cierre técnico `b622c6670db6113afd716eb67b3b08b2f037a63c`.

## Evidencia actual
- main: `e24599110f95b2f089fffd54ae013f827d3ae7ef`.
- PR #330: HEAD `c5049451047db851e98839c2086ca1ca054e38b7`, DRAFT, mergeable, 0 reviews; workflows preflight-safety-ci y deploy-staging SUCCESS. En run de deploy-staging 39217559295, jobs verify-backend/frontend SUCCESS; deploy SKIPPED para pull_request.
- PR #327: HEAD `8dac6e39aa3f68e5452e70f23ebb6bbc89c3692b`, DRAFT. Su CI 5/5 SUCCESS según informe anterior.
- El workflow de main `.github/workflows/deploy-staging.yml` mantiene `on.push.branches: [main]` y job `deploy: if: github.ref == 'refs/heads/main'` con entorno staging. El PR #330 propone condición exclusivamente manual por `workflow_dispatch`.
- Connector GitHub disponible **no ofrece lectura** de Branch protection / Rulesets ni configuración de Environment. Esos permisos y revisores siguen **NO VERIFICADOS**.

## Matriz GO/NO-GO
| Control | Evidencia de GO exigida | Actual |
|---|---|---|
| Main protegido | Captura/acta administrativa de reglas activas, required checks, required PR reviews, bypass y force push | NO-GO: no verificado |
| staging protegido | Captura/acta de required reviewers, prevención de bypass, reglas de branches/deploy | NO-GO: no verificado |
| PR #330 aprobado | Review humana documentada y SHA/CI vigentes | NO-GO: DRAFT, 0 reviews |
| Primera transición | Procedimiento y evidencia explícita que garanticen que integrar gate no despliega en VPS sin autorización | NO-GO: no demostrado |
| Workflows alternativos | Inventario y validación de workflows de push a main con capacidad de actualización remota | Parcial: deploy-staging es disparador de despliegue confirmado |
| VPS recuperación | Respaldo y restauración comprobada antes de cualquier D; sin acceso VPS ahora | No verificado; condición futura para D |

## Procedimiento de autorización propuesto
1. Responsable GitHub abre Settings → Rules → Rulesets / Branches y Settings → Environments → staging. Registra evidencia de reglas activas, reviewers, bypass y restricciones. No compartir secretos.
2. Responsable 000 audita todos los workflows `on: push main` para asegurarse de que ninguno actualice VPS fuera de una autorización específica.
3. Elaborar y aprobar una transición de **primer merge** de #330 que demuestre que no desencadena deploy. No desactivar CI, no usar bypass ni confiar en secretos faltantes; si no hay prueba suficiente, detener merge.
4. Revalidar PR #330 (SHA, reviews, CI, main HEAD), autorización formal I separada de D. Fusionar solo tras cumplir todas las condiciones y confirmar resultado del workflow en main: CI aprobado, deploy SKIPPED.
5. Revalidar #327 y su CI, reviews, SHA y compatibility. Solicitar nueva autorización I para incorporar Ítems. Verificar CI main/deploy SKIPPED.
6. Planificar D de forma independiente con commit autorizado, preflight, backup, prueba restauración aislada, Alembic real, rollback, healthcheck, rutas críticas y criterios funcionales; nunca interpretar autorización I como D.

**Decisión a fecha de esta revisión: NO-GO para I de #330 y #327.** Desarrollo probado, control administrativo sin acreditar. Ninguna operación sobre main/VPS/autorizaciones ha sido realizada.
