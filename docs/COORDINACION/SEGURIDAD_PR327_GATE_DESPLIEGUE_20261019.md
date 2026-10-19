# Revisión S — Seguridad de integración de Ítems y despliegue (2026-10-19)

## Evidencia verificada en GitHub (solo lectura)
- PR #327, HEAD `8dac6e39aa3f68e5452e70f23ebb6bbc89c3692b`, base main, DRAFT, mergeable=true (no indica aprobación), no fusionado.
- SHA main contrastado: `e24599110f95b2f089fffd54ae013f827d3ae7ef`; PR detrás de main: 0.
- Cinco workflows del HEAD #327: SUCCESS (backend, frontend, recepcion-documental-ci, roles-real-integration, roles-browser-isolated).
- Revisiones de PR #327 consultadas: **ninguna**; esto no prueba que existan protecciones de revisión requeridas.
- Workflow real `.github/workflows/deploy-staging.yml` en main: `on.push.branches: [main]`, además de `workflow_dispatch`. Job `deploy` tiene `if: github.ref == 'refs/heads/main'`, `needs: [verify-backend, verify-frontend]`, `environment: staging`; usa secretos, SSH, validaciones del host, preflight, backup/restauración, y `deploy/bootstrap-main.sh`. La fusión podría activar ese job con efecto real sobre VPS antigua si pasan las condiciones.

## Lo que NO quedó comprobado
- No existe herramienta disponible para leer API branch protection / rulesets del repositorio. No se afirma número de aprobaciones requeridas, prohibición de bypass ni lista de status checks obligatorios.
- No existe herramienta disponible para leer la política real del Environment `staging` (required reviewers, deployment branches, bypass, wait timer). La línea `environment: staging` **no demuestra aprobación humana obligatoria**.
- No se leyó la configuración/estado de secretos de despliegue ni se comprobó el servidor; no inferir que un fallo de secretos prevendría el despliegue.
- No se ejecutó SSH, deploy, modificación de settings ni acceso VPS.

## Bloqueo de seguridad y decisión
**NO AUTORIZAR I operativo** para PR #327 mientras el workflow de push a main pueda iniciar despliegue sin demostrar barrera efectiva de autorización específica.

La coordinación con el frente 000 Optimizar despliegue VPS deberá:
1. Verificar en Settings → Branches / Rules → Rulesets protección de main (PR obligatorio, checks requeridos, approvals, no bypass, restricciones de force push).
2. Verificar en Settings → Environments → staging si tiene revisores obligatorios/confirmación humana y si permite bypass; documentar evidencia de configuración sin compartir secretos.
3. Si falta la barrera, diseñar un cambio controlado (PR propio) que separe la fusión de la ejecución de deployment; mantener CI, backups, restauración y validaciones SHA. No desactivar protecciones. Probar que el push a main por sí solo **no despliega** antes de otorgar I sin autorización de D.
4. Verificar SHA de main y CI del PR inmediatamente antes de fusionar, más aprobación de revisores.

Documento de diagnóstico, no cambio de configuración. Responsable funcional Ítems sigue PR #327; 000 despliegue posee la corrección de gate de despliegue. Sin merge, sin main, sin VPS, sin deploy.
