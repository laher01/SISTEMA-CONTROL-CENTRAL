# Revisión de seguridad PR #392 — diagnóstico remoto Oracle

## Evidencia verificada
- Workflow GitHub Actions `oracle-502-readonly-diagnostic.yml`, job `verify-policy` con validación estructural YAML, permisos `contents: read`, revisión del evento/ref y configuración de entorno `staging`.
- `inspect-oracle` solo disponible en `workflow_dispatch` desde `refs/heads/main` y depende de `verify-policy`. En PR fue omitido (skipped): **no hubo SSH a Oracle**.
- Comprobaciones del destino: IP fija 132.145.233.172, usuario ubuntu, ruta /home/ubuntu/fact-central, SSH BatchMode y StrictHostKeyChecking.
- Prohibidos por verificador estático varios tokens de operaciones mutantes. Esto **no es una sandbox de comandos ni una garantía formal**: cualquier cambio posterior debe volver a revisarse.
- Los diagnósticos muestran estados y conteos, sin contenido de respuestas HTTP, credenciales o logs crudos.
- CI último commit disponible antes de esta nota: `oracle-502-readonly-diagnostic` y `pr-common-gate` aprobados.

## Controles administrativos no verificables desde la integración actual
- Protección efectiva de la rama `main`: consulta a API devolvió HTTP 403 (`Resource not accessible by integration`).
- La consulta `/rulesets` devolvió `[]`; no permite descartar reglas de organización/otras protecciones.
- No se puede comprobar por esta conexión si el environment `staging` exige revisores o restricciones de rama.
- No se puede leer ni comprobar material de secretos (correcto por seguridad); los checks de variables solo se ejecutarán si se autoriza el job manual.

## Riesgos residuales y criterio de avance
- El job remoto es de solo lectura en su versión revisada, pero el acceso SSH con credenciales de entorno supone privilegios de infraestructura; revisar alcance de la clave y proteger environment antes de integrar.
- Una integración de workflow a main puede disparar otros CI: comprobar su configuración y evitar cualquier despliegue automático no autorizado.
- No ejecutar `workflow_dispatch` antes de verificar protecciones y autorización de diagnóstico en VPS.
- Un HTTP 502 público sigue sin causa confirmada; el workflow no es una reparación.
- No se ha modificado producción, fusionado ni desplegado como parte de la revisión.

## Verificación administrativa exigida
Responsable con permisos de administración GitHub: comprobar Rulesets/Branch protection de `main`, requerimientos de PR/CI, environment `staging` (revisores, restricciones por rama), y permisos mínimos de credenciales SSH. Registrar resultados sin publicar secretos.
