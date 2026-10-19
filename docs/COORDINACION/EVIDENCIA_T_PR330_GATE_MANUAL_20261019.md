# 000 — Evidencia T sobre Gate Manual de despliegue (2026-10-19)

## GitHub verificado
- PR #330 DRAFT HEAD `c5049451047db851e98839c2086ca1ca054e38b7`; comparación con main `e24599110f95b2f089fffd54ae013f827d3ae7ef`: detrás 0, exactamente 1 línea modificada en `.github/workflows/deploy-staging.yml`.
- Workflow `preflight-safety-ci` run `39217559290`: SUCCESS; job `syntax-and-policy` SUCCESS.
- Workflow `deploy-staging` run `39217559295`: SUCCESS. Jobs `verify-backend` SUCCESS, `verify-frontend` SUCCESS; job `deploy` **SKIPPED** en evento pull_request (job 117945875539).
- Comprobación estática: condición `github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'`. Resultado lógico: pull_request→false; push main→false; workflow_dispatch sobre main→true; workflow_dispatch sobre otra rama→false. Los últimos tres escenarios son evaluación estática, no ejecución real de esos eventos.
- Permanecen `push main` para CI, `workflow_dispatch`, dependencias backend/frontend, `environment: staging`, controles de secretos y host, SHA `EXPECTED_COMMIT`, preflight SSH, backup/restauración y `bootstrap-main.sh`.
- PR #327 (Ítems) HEAD `8dac6e39aa3f68e5452e70f23ebb6bbc89c3692b`: comparación main detrás 0, archivos en backend/frontend/docs, sin solapamiento con workflow modificado por PR #330. CI de #327 verificado previamente 5/5.

## Limitaciones y condiciones NO-GO
- No hay herramienta autorizada para inspeccionar los rulesets/branch protection reales de main, Environment staging, required reviewers o bypass. No afirmar aprobación humana obligatoria.
- No se ejecutó push main, workflow_dispatch, despliegue, VPS ni restauración real. Job skipped de pull_request demuestra solo ese evento.
- **Primera fusión de PR #330:** mientras main contiene la definición anterior, un push a main puede iniciar deploy con el workflow resultante, sujeto a la semántica de Actions y sus controles; no autorizar esa primera fusión hasta contar con un procedimiento de transición respaldado y aprobado específicamente.
- Mantener #330 y #327 en DRAFT, no fusionar ni modificar main. Reconfirmar SHA y controles antes de I.

**Próximo paso:** R/S con equipo 000 para comprobar reglas reales y diseñar transición de la primera integración sin despliegue; solo luego evaluar I con autorización expresa separada de D.
