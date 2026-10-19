# S — Revisión de seguridad: transición del gate de despliegue PR #330

Fecha 2026-10-19. Diagnóstico, sin cambio a main o VPS.

## Evidencias GitHub
- PR #330 DRAFT HEAD `c5049451047db851e98839c2086ca1ca054e38b7`, mergeable=true; CI `preflight-safety-ci` 39217559290 SUCCESS; `deploy-staging` 39217559295 SUCCESS; jobs `verify-backend` SUCCESS, `verify-frontend` SUCCESS y `deploy` SKIPPED.
- PR #327 DRAFT HEAD `8dac6e39aa3f68e5452e70f23ebb6bbc89c3692b`, mergeable=true. PR #330: 0 revisiones registradas.
- main SHA `e24599110f95b2f089fffd54ae013f827d3ae7ef` todavía contiene `if: github.ref == 'refs/heads/main'` en `.github/workflows/deploy-staging.yml` con `on.push.branches: [main]` y `environment: staging`.
- El commit de PR #330 cambia únicamente esta condición a `github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'`, sin eliminar verificaciones previas, preflight, secretos, backup/restauración o bootstrap.

## Limitaciones
- Las herramientas GitHub conectadas no exponen branch protection/rulesets ni Settings → Environments → staging; **no se han comprobado** aprobaciones obligatorias, bypass, reglas de despliegue y required checks. No se ha consultado ni alterado ningún secreto.
- Un job `skipped` en `pull_request` NO prueba el comportamiento de un `push` a main. La semántica del workflow propuesto permite inferir que un push no satisface el predicado, pero la primera transición debe validarse de forma segura. No se ha probado en VPS.

## Procedimiento de transición recomendado para responsable 000
1. Verificar administrativamente en GitHub Settings las reglas activas de main y Environment staging, required reviewers y bypass; preservar todas las protecciones. Registrar capturas o acta de evidencia sin exponer secretos.
2. Someter #330 a revisión técnica, comprobar que el SHA de main y #330 no cambiaron, y contrastar **todos** los workflows que pudieran desplegar ante push a main.
3. Para la **primera integración del gate**, acordar y autorizar un procedimiento que impida ejecución no autorizada del job antiguo; no desactivar CI ni protección de seguridad, ni utilizar bypass. Si no se puede garantizar el aislamiento, detener I y escalar decisión.
4. Una vez autorizada e integrada la solución de gate, demostrar sobre GitHub Actions que en push a main las verificaciones aprueban y deploy es SKIPPED, sin acceder a VPS; mantener disparo manual de D sujeto a permisos y controles explícitos.
5. Solo entonces revisar aprobación y CI de #327 y pasar a I con autorización separada de D.

Estado: **NO-GO** para merge de #330/#327; **GO** para validación administrativa y revisión técnica previa. No merge, no main, no VPS, no deploy.
