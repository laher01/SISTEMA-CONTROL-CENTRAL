# 000 Optimizar despliegue VPS — coordinación Gate S para PR #327

Fecha: 2026-10-19. Diagnóstico documental, **no implementación del cambio**.

## Punto de partida comprobado
- PR #327 (Ítems) DRAFT, HEAD `8dac6e39aa3f68e5452e70f23ebb6bbc89c3692b`, CI 5/5 SUCCESS, 0 reviews registrados, sin divergencia respecto de main `e24599110f95b2f089fffd54ae013f827d3ae7ef` en la verificación.
- Informe original: `docs/COORDINACION/SEGURIDAD_PR327_GATE_DESPLIEGUE_20261019.md` del commit `ece59ba28730b714ef336cbb9be899f9ee209a6a`.
- `.github/workflows/deploy-staging.yml` tiene `on.push.branches: [main]`, además de `workflow_dispatch`. El job `deploy` tiene `if: github.ref == 'refs/heads/main'` sin comprobar evento manual. Depende de `verify-backend` y `verify-frontend`, usa `environment: staging`, SSH, preflight, backup/restauración, bootstrap commit. Por tanto, un merge podría iniciar el job.
- La presencia de `environment: staging` **no permite inferir** que hay revisores obligatorios. No se dispone de acción de lectura de Branch protection, Repository rulesets ni Environment protection. **Sin prueba de un Gate humano, no se autoriza I efectivo.**

## Propuesta para que el dueño del workflow implemente en PR independiente
Mantener `push main` para verificaciones CI, pero hacer que `deploy` solo se ejecute en solicitud manual explícita sobre main. Cambiar **solo el predicado del job**, tras revisión y pruebas del dueño:

```yaml
  deploy:
    if: github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'
    needs: [verify-backend, verify-frontend]
    runs-on: ubuntu-latest
    environment: staging
```

Preservar pasos de validación de secretos, host, SHA, preflight, respaldo, restauración y bootstrap; no ejecutar workflows ni cambiar secrets durante esta revisión. Esto desacopla el disparador de push en el código del workflow propuesto; **hasta que el cambio haya sido integrado de forma segura en main, el workflow actual sigue permitiendo intento de despliegue tras push**. El mero PR de la propuesta no protege la producción.

## Verificaciones obligatorias, responsabilidad 000
1. GitHub Settings → Rules → Rulesets y Branches → Branch protection: existencia y alcance de reglas para `main`, PR/reviews exigidas, checks requeridos, prohibición force push/bypass (incluido administrador). Documentar evidencia sin publicar secretos.
2. Settings → Environments → staging: Required reviewers, bypass permitido o prohibido, restricciones de ramas para despliegue. Documentar evidencia.
3. Preparar PR independiente con desacoplamiento del job; demostrar que `push main` ejecuta verificación **sin deploy** y que `workflow_dispatch` exige aprobación y mantiene recuperación. El primer cambio de gate requerirá un procedimiento expresamente aprobado para no disparar accidentalmente el workflow anterior.
4. Comprobar entorno de staging, respaldos y restauración antes de cualquier `D`. No tratar CI pytest de base efímera como garantía de recuperación VPS.
5. Revisar y aprobar PR #327; volver a verificar SHA main/HEAD/CI inmediatamente antes de `I`.

## Decisión
**NO-GO para ejecutar fusión I en este momento.** GO para preparar/revisar cambio de gate en rama y para comprobación administrativa de GitHub Settings por persona autorizada. Sin acceso VPS, sin merge, sin despliegue y sin cambio de main.
